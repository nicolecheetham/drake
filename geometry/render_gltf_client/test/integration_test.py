"""Conducts integration tests by exercising the entire RPC pipeline that
contains a render client and a render server.  The tests then inspect the
generated images or glTF files by comparing them with the expected output.

As different renderers may have various rounding errors or subtle lighting
settings, two heuristic thresholds are applied, i.e., a per-pixel threshold for
each image type and an overall percentage threshold for invalid pixels.

Two images are considered close enough if the majority of the pixels are within
the per-pixel threshold.  The ground truth images are generated by
RenderEngineVtk."""

import glob
from multiprocessing import Process, Queue
import os
import subprocess
import sys
import re
import unittest

from bazel_tools.tools.python.runfiles.runfiles import Create as CreateRunfiles
import numpy as np
from PIL import Image

from drake.geometry.render_gltf_client.test.server_demo import app

COLOR_PIXEL_THRESHOLD = 20  # RGB pixel value tolerance.
DEPTH_PIXEL_THRESHOLD = 0.001  # Depth measurement tolerance in meters.
LABEL_PIXEL_THRESHOLD = 0
INVALID_PIXEL_FRACTION = 0.1

# TODO(zachfang): Add another test for glTF verification.


class MultiprocessingStdout:
    """A replacement for stdout that duplicates its data to a multiprocessing
    Queue in addition to stdout.
    """

    def __init__(self, queue):
        self.queue = queue

    def write(self, data):
        sys.__stdout__.write(data)
        self.queue.put(data)

    def flush(self):
        sys.__stdout__.flush()


def run_server(stdout_queue):
    """The entry point for the server process.
    Runs the Flask app, with stdout copied to the given queue so that we can
    scrape its output to find the port number.
    """
    new_stdout = MultiprocessingStdout(stdout_queue)
    sys.stdout = new_stdout
    sys.stderr = new_stdout
    app.run(host="127.0.0.1", port=0)


class TestIntegration(unittest.TestCase):
    def setUp(self):
        self.runfiles = CreateRunfiles()

        # Start the server on the other process.
        stdout_queue = Queue()
        self.server_proc = Process(target=run_server, args=(stdout_queue,))
        self.server_proc.start()

        # Wait to hear which port it's using.
        self.server_port = None
        while self.server_port is None:
            data = stdout_queue.get()
            match = re.search(r"Running on http://127.0.0.1:([0-9]+)/ ", data)
            if match:
                (self.server_port,) = match.groups()

    def tearDown(self):
        self.server_proc.kill()

    def render_demo_images(self, renderer):
        """Renders images to a temporary folder and returns the curated image
        paths.
        """
        tmp_dir = os.path.join(os.environ.get("TEST_TMPDIR", "/tmp"), renderer)
        os.makedirs(tmp_dir, exist_ok=True)

        client_demo = self.runfiles.Rlocation(
            "drake/geometry/render_gltf_client/client_demo"
        )

        render_args = [
            client_demo,
            f"--render_engine={renderer}",
            "--simulation_time=0.1",
            f"--save_dir={tmp_dir}",
            f"--server_base_url=127.0.0.1:{self.server_port}",
        ]
        subprocess.run(render_args, check=True)

        # The folder is assumed to contain at least 2 sets of color, depth, and
        # label images for inspection.
        image_sets = []
        for index in range(2):
            image_set = [
                f"{tmp_dir}/color_{index:03d}.png",
                f"{tmp_dir}/depth_{index:03d}.tiff",
                f"{tmp_dir}/label_{index:03d}.png",
            ]
            image_sets.append(image_set)
        return image_sets

    def assert_error_fraction_less(self, image_diff, fraction):
        image_diff_fraction = np.count_nonzero(image_diff) / image_diff.size
        self.assertLess(image_diff_fraction, fraction)

    def test_integration(self):
        vtk_image_sets = self.render_demo_images("vtk")
        client_image_sets = self.render_demo_images("client")

        for vtk_image_paths, client_image_paths in zip(
            vtk_image_sets, client_image_sets
        ):
            # Load the images and convert them to numpy arrays.
            vtk_color, vtk_depth, vtk_label = (
                np.array(Image.open(image_path))
                for image_path in vtk_image_paths
            )
            client_color, client_depth, client_label = (
                np.array(Image.open(image_path))
                for image_path in client_image_paths
            )

            # Convert uint8 images to float data type to avoid overflow during
            # calculation.
            color_diff = (
                np.absolute(
                    vtk_color.astype(float) - client_color.astype(float)
                )
                > COLOR_PIXEL_THRESHOLD
            )
            self.assert_error_fraction_less(color_diff, INVALID_PIXEL_FRACTION)

            # Set the infinite values in depth images to zero.
            vtk_depth[~np.isfinite(vtk_depth)] = 0.0
            client_depth[~np.isfinite(client_depth)] = 0.0
            depth_diff = (
                np.absolute(vtk_depth - client_depth) > DEPTH_PIXEL_THRESHOLD
            )
            self.assert_error_fraction_less(depth_diff, INVALID_PIXEL_FRACTION)

            label_diff = (
                np.absolute(vtk_label - client_label) > LABEL_PIXEL_THRESHOLD
            )
            self.assert_error_fraction_less(label_diff, INVALID_PIXEL_FRACTION)