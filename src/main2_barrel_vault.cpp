#include "geometrycentral/surface/manifold_surface_mesh.h"
#include "geometrycentral/surface/meshio.h"
#include "geometrycentral/surface/vertex_position_geometry.h"

#include "geometrycentral/surface/direction_fields.h"

#include "polyscope/polyscope.h"
#include "polyscope/surface_mesh.h"
#include "polyscope/curve_network.h"
#include "path_extraction.h"

#include <igl/readOBJ.h>
#include <igl/loop.h>
#include <igl/upsample.h>
#include <igl/writeOBJ.h>
//#include <igl/copyleft/comiso/nrosy.h>

#include "imgui.h"
#include <fstream>
#include <vector>


#include "path_extraction.h"

#include "parameterization.h"
#include "stretch_angles.h"
//#include "stripe_patterns.h"
#include "timer.h"

#include <geometrycentral/surface/direction_fields.h>
#include <geometrycentral/surface/manifold_surface_mesh.h>
#include <geometrycentral/surface/stripe_patterns.h>
#include "geometrycentral/surface/vector_heat_method.h"

#include <igl/boundary_loop.h>
#include <igl/ramer_douglas_peucker.h>

#ifdef USE_ORTOOLS
#include <ortools/constraint_solver/routing.h>
#include <ortools/constraint_solver/routing_enums.pb.h>
#include <ortools/constraint_solver/routing_index_manager.h>
#include <ortools/constraint_solver/routing_parameters.h>
#endif

#ifdef USE_PARDISO
#include <Eigen/PardisoSupport>
using LDLTSolver = Eigen::PardisoLDLT<Eigen::SparseMatrix<double>>;
using LLTSolver = Eigen::PardisoLLT<Eigen::SparseMatrix<double>>;
using LUSolver = Eigen::PardisoLU<Eigen::SparseMatrix<double>>;
#else
using LDLTSolver = Eigen::SimplicialLDLT<Eigen::SparseMatrix<double>>;
using LLTSolver = Eigen::SimplicialLLT<Eigen::SparseMatrix<double>>;
using LUSolver = Eigen::SparseLU<Eigen::SparseMatrix<double>>;
#endif // USE_PARDISO

using namespace geometrycentral;
using namespace geometrycentral::surface;


// Specify the file path
// MODIFY -----------------------------------------------------------------
//std::string directory = "/Users/duch/Documents/PhD/knit/2024_prototypes/4part/0918/";
//std::string filename = "4part_half_dense";
//std::string directory = "/Users/duch/Documents/PhD/knit/2024_prototypes/4part/1030/";
//std::string filename = "half4parts_mm";
std::string directory = "/Users/duch/Documents/PhD/paper/iass_2024/";
std::string filename = "barrel_vault";

//  -----------------------------------------------------------------

// obj
std::string pathToFile = directory + filename + ".obj";
// vector field
std::string filePath = directory + filename + "_vertex_directional_field.txt";
// remesh obj
std::string outToFile = directory + filename + "_remesh.obj";
// polyline string
std::string polylineToFile = directory + filename + "_tri_path.txt";



Eigen::MatrixXd loadMatrixFromFile(const std::string& filePath) {
  std::ifstream file(filePath);

  // Check if the file is open
  if (!file.is_open()) {
    std::cerr << "Could not open the file - '" << filePath << "'" << std::endl;
    return Eigen::MatrixXd(); // Return an empty matrix
  }

  std::vector<double> matrixEntries;
  int numRows = 0;
  std::string line;

  // Read the file line by line
  while (getline(file, line)) {
    std::istringstream iss(line);
    double num;
    while (iss >> num) {
      matrixEntries.push_back(num);
    }
    ++numRows;
  }

  // Assuming the matrix is not empty and it's a proper rectangle
  if (numRows == 0) {
    std::cerr << "Matrix is empty or not properly formatted" << std::endl;
    return Eigen::MatrixXd(); // Return an empty matrix
  }
  int numCols = matrixEntries.size() / numRows;

  // Create an Eigen matrix and fill it with the values
  Eigen::MatrixXd mat(numRows, numCols);
  for (int i = 0; i < numRows; ++i) {
    for (int j = 0; j < numCols; ++j) {
      mat(i, j) = matrixEntries[i * numCols + j];
    }
  }

  file.close(); // Close the file
  return mat;
}


std::unique_ptr<ManifoldSurfaceMesh> mesh;
std::unique_ptr<VertexPositionGeometry> geometry;

// Polyscope visualization handle, to quickly add data to the surface
polyscope::SurfaceMesh *psMesh;

// Some algorithm parameters
float param1 = 42.0;

// Example computation function -- this one computes and registers a scalar
// quantity
void doWork() {
  polyscope::warning("Computing Gaussian curvature.\nalso, parameter value = " +
                     std::to_string(param1));

  geometry->requireVertexGaussianCurvatures();
  psMesh->addVertexScalarQuantity("curvature",
                                  geometry->vertexGaussianCurvatures,
                                  polyscope::DataType::SYMMETRIC);
}

// A user-defined callback, for creating control panels (etc)
// Use ImGUI commands to build whatever you want here, see
// https://github.com/ocornut/imgui/blob/master/imgui.h
void myCallback() {

  if (ImGui::Button("do work")) {
    doWork();
  }

  ImGui::SliderFloat("param", &param1, 0., 100.);
}

int main(int argc, char **argv) {

  Eigen::MatrixXd V;
  Eigen::MatrixXi F;
//  std::string pathToFile = "/Users/duch/Downloads/pillow_uni.obj";
//  std::string pathToFile = "/Users/duch/Documents/PhD/DF2024/prototype_tri.obj";
//  std::string pathToFile ="/Users/duch/Documents/PhD/paper/2024_fofin/circular.obj";

//  std::string pathToFile = "/Users/duch/Downloads/butt_out.obj";
  igl::readOBJ(pathToFile, V, F);

  double scale_factor = (V.colwise().maxCoeff() - V.colwise().minCoeff()).maxCoeff();
  // resize mesh to a 1200mm width
  V *= 1200.0 / scale_factor;
//  V.col(1) *= -1;

//  // subdivide until number of mesh faces is at least nFmin
//  // TODO: change this remesh step before generating the field
//  int nFmin = 100;
//  if(argc == 3)
//    nFmin = std::stoi(argv[2]);
//  while(F.rows() < nFmin)
//  {
//    Eigen::MatrixXd tempV = V;
//    Eigen::MatrixXi tempF = F;
////    igl::loop(tempV, tempF, V, F);
//    igl::upsample(tempV, tempF, V, F);
//  }
//  // Path to save the OBJ file
////  std::string outToFile = "/Users/duch/Documents/PhD/DF2024/prototype_tri_remesh.obj";



////  std::string outToFile = "/Users/duch/Downloads/butt_out_sized.obj";
  igl::writeOBJ(outToFile, V, F);
//
//  // create geometry-central objects
  std::tie(mesh, geometry) = readManifoldSurfaceMesh(outToFile);
//  std::tie(mesh, geometry) = readManifoldSurfaceMesh(pathToFile);


  // Compute the stripe pattern
//  double spacing = 3.63;
  std::cout << "The coefficiency is: " << scale_factor << std::endl;
  double spacing = 4.532151655555558 / scale_factor * 1000; // at zero stress

//  double spacing = 4.66205136 / scale_factor * 1000; // at force 25N

  VertexData<double> frequencies(*mesh, 1.0 / spacing);

  // Set vertex tangent spaces
  geometry->requireVertexTangentBasis();
  VertexData<Vector3> vBasisX(*mesh);
  VertexData<Vector3> vBasisY(*mesh);
  for (Vertex v : mesh->vertices()) {
    vBasisX[v] = geometry->vertexTangentBasis[v][0];
    vBasisY[v] = geometry->vertexTangentBasis[v][1];
  }


//  VertexData<Vector2> directionField(*mesh);
//  std::string filePath = "/Users/duch/Downloads/vertex_directional_field.txt";
//  auto VD = loadMatrixFromFile(filePath);
//  std::cout << VD.rows() << "," << VD.cols() << std::endl;
//  std::cout << V.rows() << std::endl;
//  Vector3 RefVec;
//  double projectionX;
//  double projectionY;
//
//  for (Vertex v : mesh->vertices()) {
//    int index = v.getIndex();
//    RefVec.x = VD(index, 0);
//    RefVec.y = VD(index, 1);
//    RefVec.z = VD(index, 2);
//
//    projectionX = dot(RefVec, geometry->vertexTangentBasis[v][0]);
//    projectionY = dot(RefVec, geometry->vertexTangentBasis[v][1]);
//
//    Vector2 dir = {projectionX, projectionY};
//    dir = unit(dir);
//
//    directionField[v] = dir;
//  }



//  std::string filePath = "/Users/duch/Documents/PhD/paper/2024_fofin/vertex_directional_field.txt";

  auto VD = loadMatrixFromFile(filePath);

//  std::cout << VD.row(0) << "," << VD.row(6) << std::endl;

//  // manual modification
//  std::vector<int> bdrs_vs = {0, 6, 411, 414, 416, 418,420, 422, 424, 426, 428, 430, 432, 434, 436, 438,439, 325, 323, 322, 149, 148, 7, 1};
//  for(int i : bdrs_vs) {
//    VD.row(i) << 1.0, 0.0, 0.0;
//  }


  VertexData<Vector2> originalField(*mesh);
  std::cout << VD.rows() << "," << VD.cols() << std::endl;
  std::cout << mesh->nVertices() << std::endl;

  Vector3 RefVec;
  double projectionX;
  double projectionY;

  for (Vertex v : mesh->vertices()) {
    int index = v.getIndex();
    RefVec.x = VD(index, 0);
    RefVec.y = VD(index, 1);
    RefVec.z = VD(index, 2);

    projectionX = dot(RefVec, geometry->vertexTangentBasis[v][0]);
    projectionY = dot(RefVec, geometry->vertexTangentBasis[v][1]);

    Vector2 dir = {projectionX, projectionY};
    dir = unit(dir);

    originalField[v] = dir;
  }

  VectorHeatMethodSolver solver(*geometry);
  Vertex sourceVert = mesh->vertex(358);
  Vector2 sourceVec = {0.0, 1.0};
//  VertexData<Vector2> originalField = solver.transportTangentVector(sourceVert, sourceVec);

  VertexData<Vector2> directionField(*mesh);
  for(Vertex v : mesh->vertices()) {
    size_t i = v.getIndex();

    std::complex<double> z(originalField[i].x, originalField[i].y);
    // Apply the square root operation to achieve 2-symmetry
    std::complex<double> zRoot = std::pow(z, 2);
    Vector2 sr ={real(zRoot), imag(zRoot)}; // Convert back to Vector2

    // Convert back to Vector2
    directionField[v] = sr;
  }

//      VertexData<Vector2> directionField = geometrycentral::surface::computeSmoothestVertexDirectionField(*geometry, 2);

//  VertexData<Vector2> directionField = geometrycentral::surface::computeCurvatureAlignedVertexDirectionField(*geometry, 2);
//  for (Vertex v : mesh->vertices()) {
//    std::cout << directionField[v] << "and v is " << v << std::endl;
//  }
//  VertexData<Vector2> directionField = geometrycentral::surface::computeSmoothestBoundaryAlignedVertexDirectionField(*geometry, 2);


  CornerData<double> stripeValues;
  FaceData<int> stripeIndices, fieldIndices;
  std::tie(stripeValues, stripeIndices, fieldIndices) = computeStripePattern(*geometry, frequencies, directionField);




  const auto& [points, edges]  =  extractPolylinesFromStripePattern(*geometry, stripeValues, stripeIndices, fieldIndices, directionField,
                                           true);

//  const auto& [points, edges] = computeStripePatternPolylines(*geometry, frequencies, directionField, false);
  auto polylines = edgeToPolyline(points, edges);
  double timeLimit = 10;
//  polylines = orderPolylines(polylines, *geometry, timeLimit);




  std::ofstream file(polylineToFile);
  for (const auto& polyline : polylines) {
    for (size_t i = 0; i < polyline.size(); ++i) {
      const auto& point = polyline[i];
      file << point[0] << "," << point[1] << "," << point[2];
      if (i < polyline.size() - 1) {
        file << "; ";
      }
    }
    file << "\n"; // Newline to separate polylines
  }
  file.close();

  // Initialize polyscope
  polyscope::init();

  // Set the callback function
  polyscope::state::userCallback = myCallback;



  // Register the mesh with polyscope
  psMesh = polyscope::registerSurfaceMesh(
      //      polyscope::guessNiceNameFromPath(args::get(inputFilename)),
      "my_mesh",
      geometry->inputVertexPositions, mesh->getFaceVertexList(),
      polyscopePermutations(*mesh));



//    psMesh->addVertexTangentVectorQuantity("VF", vField, vBasisX, vBasisY);
  psMesh->addVertexTangentVectorQuantity("VF", directionField, vBasisX, vBasisY, 1);
  psMesh->addVertexTangentVectorQuantity("OF", originalField, vBasisX, vBasisY, 2);

//   show polyline

  for (size_t i = 0; i < polylines.size(); ++i) {
    std::vector<Vector3> polyPoints; // Polyscope usually works with glm::vec3 for 3D points
    std::vector<std::vector<size_t>> polylineIndices;
    for (const auto& pt : polylines[i]) {
      polyPoints.push_back(pt);
    }
    for (size_t k = 0; k < polylines[i].size() - 1; k++) {
      polylineIndices.push_back({k, k + 1});
    }
    // Register the polyline with Polyscope
    // Note: Each polyline must have a unique name, hence the use of the index i in the name
    auto curveNet = polyscope::registerCurveNetwork("Polyline " + std::to_string(i), polyPoints, polylineIndices);
    curveNet->setRadius(0.001);
  }


  // Give control to the polyscope gui
  polyscope::show();

  return EXIT_SUCCESS;
}