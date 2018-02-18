#include <pybind11/eigen.h>
#include <pybind11/pybind11.h>

#include "drake/bindings/pydrake/pydrake_pybind.h"
#include "drake/systems/primitives/adder.h"
#include "drake/systems/primitives/affine_system.h"
#include "drake/systems/primitives/barycentric_system.h"
#include "drake/systems/primitives/constant_value_source.h"
#include "drake/systems/primitives/constant_vector_source.h"
#include "drake/systems/primitives/integrator.h"
#include "drake/systems/primitives/linear_system.h"
#include "drake/systems/primitives/signal_logger.h"
#include "drake/systems/primitives/zero_order_hold.h"

namespace drake {
namespace pydrake {

PYBIND11_MODULE(primitives, m) {
  // NOLINTNEXTLINE(build/namespaces): Emulate placement in namespace.
  using namespace drake::systems;

  m.doc() = "Bindings for the primitives portion of the Systems framework.";

  using T = double;

  py::class_<Adder<T>, LeafSystem<T>>(m, "Adder").def(py::init<int, int>());

  py::class_<AffineSystem<T>, LeafSystem<T>>(m, "AffineSystem")
      .def(py::init<const Eigen::Ref<const Eigen::MatrixXd>&,
                    const Eigen::Ref<const Eigen::MatrixXd>&,
                    const Eigen::Ref<const Eigen::VectorXd>&,
                    const Eigen::Ref<const Eigen::MatrixXd>&,
                    const Eigen::Ref<const Eigen::MatrixXd>&,
                    const Eigen::Ref<const Eigen::VectorXd>&, double>(),
           py::arg("A"), py::arg("B"), py::arg("f0"), py::arg("C"),
           py::arg("D"), py::arg("y0"), py::arg("time_period") = 0.0)
      // TODO(eric.cousineau): Fix these to return references instead of copies.
      .def("A",
           overload_cast_explicit<const Eigen::MatrixXd&>(&AffineSystem<T>::A))
      .def("B",
           overload_cast_explicit<const Eigen::MatrixXd&>(&AffineSystem<T>::B))
      .def("f0",
           overload_cast_explicit<const Eigen::VectorXd&>(&AffineSystem<T>::f0))
      .def("C",
           overload_cast_explicit<const Eigen::MatrixXd&>(&AffineSystem<T>::C))
      .def("D",
           overload_cast_explicit<const Eigen::MatrixXd&>(&AffineSystem<T>::D))
      .def("y0",
           overload_cast_explicit<const Eigen::VectorXd&>(&AffineSystem<T>::y0))
      .def("time_period", &AffineSystem<T>::time_period);

  py::class_<BarycentricMeshSystem<T>, LeafSystem<T>>(m,
                                                      "BarycentricMeshSystem")
      .def(py::init<math::BarycentricMesh<T>,
                    const Eigen::Ref<const MatrixX<T>>&>())
      .def("get_mesh", &BarycentricMeshSystem<T>::get_mesh)
      .def("get_output_values", &BarycentricMeshSystem<T>::get_output_values);

  py::class_<ConstantValueSource<T>, LeafSystem<T>>(m, "ConstantValueSource");

  py::class_<ConstantVectorSource<T>, LeafSystem<T>>(m, "ConstantVectorSource")
      .def(py::init<VectorX<T>>());

  py::class_<Integrator<T>, LeafSystem<T>>(m, "Integrator")
      .def(py::init<int>());

  py::class_<LinearSystem<T>, AffineSystem<T>>(m, "LinearSystem")
      .def(py::init<const Eigen::Ref<const Eigen::MatrixXd>&,
                    const Eigen::Ref<const Eigen::MatrixXd>&,
                    const Eigen::Ref<const Eigen::MatrixXd>&,
                    const Eigen::Ref<const Eigen::MatrixXd>&, double>(),
           py::arg("A"), py::arg("B"), py::arg("C"), py::arg("D"),
           py::arg("time_period") = 0.0);

  py::class_<SignalLogger<T>, LeafSystem<T>>(m, "SignalLogger")
      .def(py::init<int>())
      .def(py::init<int, int>())
      .def("sample_times", &SignalLogger<T>::sample_times)
      .def("data", &SignalLogger<T>::data);

  py::class_<ZeroOrderHold<T>, LeafSystem<T>>(m, "ZeroOrderHold")
      .def(py::init<double, int>());

  // TODO(eric.cousineau): Add more systems as needed.
}

}  // namespace pydrake
}  // namespace drake
