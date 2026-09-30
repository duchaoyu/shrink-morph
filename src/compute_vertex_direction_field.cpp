// Standalone helper: computes a per-vertex direction field for a triangle
// mesh and writes it as a "_vertex_directional_field.txt" file in the format
// expected by main2.cpp's loadMatrixFromFile (one "x y z" world space vector
// per vertex, in the same order as the input OBJ's vertices).
//
// Field types:
//   curvature       - aligned with the principal curvature directions (one
//                     of the two orthogonal directions)
//   boundary        - a single constant world-space direction, copied to
//                     every vertex: the direction normal to the boundary
//                     curve (in the tangent plane) at the "middle" of the
//                     boundary opening, taken as the boundary vertex with
//                     the greatest height (the arch apex/crown of the
//                     opening). main2.cpp's own pipeline re-projects this
//                     constant world vector onto each vertex's local
//                     tangent plane, so there is no smoothing or transport
//                     step to introduce rotation - it's the same direction
//                     everywhere.
//   boundary_smooth - the older harmonic (smoothest connection Laplacian)
//                     boundary-aligned field. Kept only for comparison.
//   boundary_transport - vector-heat-method transport from every boundary
//                     vertex's own local direction. Also kept for
//                     comparison.
//   anticlastic     - every vertex is pinned to the tangent-plane projection
//                     of world direction (0,1,0), except the handful of
//                     vertices where that projection is nearly degenerate
//                     (surface normal nearly parallel to (0,1,0), e.g. the
//                     vault's ridge crest and the boundary opening's crown)
//                     - those are filled in via vector-heat-method transport
//                     from their neighbors instead.
//   rotate90        - reads an existing field file (4th argument) and
//                     rotates every vertex's vector 90 degrees within its
//                     own tangent plane (not about one fixed 3D axis).
//
// Usage: compute_vertex_direction_field <input.obj> <output.txt> [curvature|boundary|boundary_smooth|boundary_transport|anticlastic|rotate90] [existing_field.txt]

#include "geometrycentral/numerical/linear_solvers.h"
#include "geometrycentral/surface/direction_fields.h"
#include "geometrycentral/surface/manifold_surface_mesh.h"
#include "geometrycentral/surface/meshio.h"
#include "geometrycentral/surface/vector_heat_method.h"
#include "geometrycentral/surface/vertex_position_geometry.h"

#include <igl/readOBJ.h>

#include <complex>
#include <fstream>
#include <iostream>
#include <limits>

using namespace geometrycentral;
using namespace geometrycentral::surface;

// Direction normal to the boundary curve (in the tangent plane) at a
// boundary vertex, as an ordinary (non-power-representation) tangent vector.
// Mirrors the construction used internally by
// computeSmoothestBoundaryAlignedVertexDirectionField, minus the ^nSym step.
Vector2 boundaryNormalDirection(VertexPositionGeometry& geometry, Vertex v) {
  Halfedge heBoundaryA = v.halfedge();
  Halfedge heBoundaryB = heBoundaryA.twin().next();
  Vector2 vecA = geometry.halfedgeVectorsInVertex[heBoundaryA];
  Vector2 vecB = geometry.halfedgeVectorsInVertex[heBoundaryB];
  Vector2 tangentV = unit(-vecA + vecB);
  return tangentV.rotate90();
}

// geometrycentral keeps its connection-Laplacian assembly private to
// direction_fields.cpp (anonymous namespace), so it isn't reusable from
// here. This is the same construction (Levi-Civita connection Laplacian,
// power nSym, cotan weights, tiny identity shift to avoid singularity),
// built only from public IntrinsicGeometryInterface quantities.
SparseMatrix<std::complex<double>> vertexConnectionLaplacian(IntrinsicGeometryInterface& geometry, int nSym) {
  SurfaceMesh& mesh = geometry.mesh;
  geometry.requireVertexIndices();
  geometry.requireEdgeCotanWeights();
  geometry.requireTransportVectorsAlongHalfedge();

  std::vector<Eigen::Triplet<std::complex<double>>> triplets;
  for (Halfedge he : mesh.halfedges()) {
    size_t iTail = geometry.vertexIndices[he.vertex()];
    size_t iTip = geometry.vertexIndices[he.next().vertex()];
    Vector2 rot = geometry.transportVectorsAlongHalfedge[he.twin()].pow(nSym);
    double weight = geometry.edgeCotanWeights[he.edge()];
    triplets.emplace_back(iTail, iTail, weight);
    triplets.emplace_back(iTail, iTip, -weight * rot);
  }
  Eigen::SparseMatrix<std::complex<double>> L(mesh.nVertices(), mesh.nVertices());
  L.setFromTriplets(triplets.begin(), triplets.end());
  Eigen::SparseMatrix<std::complex<double>> eye(mesh.nVertices(), mesh.nVertices());
  eye.setIdentity();
  L += 1e-9 * eye;
  return L;
}

// Smoothest nSym-symmetric field with fixed (Dirichlet) values at an
// arbitrary subset of vertices, generalizing
// computeSmoothestBoundaryAlignedVertexDirectionField's "fixed at mesh
// boundary" to "fixed at any prescribed vertex set".
VertexData<Vector2> computeConstrainedSmoothestField(VertexPositionGeometry& geometry,
                                                       const VertexData<char>& isConstrained,
                                                       const VertexData<std::complex<double>>& constrainedValues,
                                                       int nSym) {
  SurfaceMesh& mesh = geometry.mesh;
  geometry.requireVertexGalerkinMassMatrix();
  geometry.requireVertexIndices();

  SparseMatrix<std::complex<double>> massMatrix = geometry.vertexGalerkinMassMatrix.cast<std::complex<double>>();
  SparseMatrix<std::complex<double>> energyMatrix = vertexConnectionLaplacian(geometry, nSym);

  Vector<std::complex<double>> b(mesh.nVertices());
  b.setZero();

  for (Vertex v : mesh.vertices()) {
    if (isConstrained[v]) continue;
    size_t i = geometry.vertexIndices[v];
    for (Halfedge he : v.incomingHalfedges()) {
      Vertex neighbor = he.vertex();
      if (isConstrained[neighbor]) {
        size_t j = geometry.vertexIndices[neighbor];
        std::complex<double> Aij = energyMatrix.coeff(i, j);
        energyMatrix.coeffRef(i, j) = 0;
        b(i) += -Aij * constrainedValues[neighbor];
      }
    }
  }

  Eigen::SparseMatrix<std::complex<double>, Eigen::ColMajor> LHS = energyMatrix;
  Eigen::VectorXcd RHS = massMatrix * b;
  Eigen::VectorXcd solution = solveSquare(LHS, RHS);

  VertexData<Vector2> toReturn(mesh);
  for (Vertex v : mesh.vertices()) {
    if (isConstrained[v]) {
      toReturn[v] = Vector2::fromComplex(constrainedValues[v]);
    } else {
      toReturn[v] = unit(Vector2::fromComplex(solution(geometry.vertexIndices[v])));
    }
  }
  return toReturn;
}

int main(int argc, char** argv) {
  if (argc < 3 || argc > 5) {
    std::cerr
        << "Usage: " << argv[0]
        << " <input.obj> <output.txt> [curvature|boundary|boundary_smooth|boundary_transport|anticlastic|rotate90] "
           "[existing_field.txt (rotate90 only)]"
        << std::endl;
    return EXIT_FAILURE;
  }
  std::string inputPath = argv[1];
  std::string outputPath = argv[2];
  std::string fieldType = argc >= 4 ? argv[3] : "curvature";
  std::string existingFieldPath = argc == 5 ? argv[4] : "";

  std::unique_ptr<ManifoldSurfaceMesh> mesh;
  std::unique_ptr<VertexPositionGeometry> geometry;
  std::tie(mesh, geometry) = readManifoldSurfaceMesh(inputPath);

  std::cout << "Loaded mesh with " << mesh->nVertices() << " vertices, " << mesh->nFaces() << " faces" << std::endl;

  geometry->requireVertexTangentBasis();
  geometry->requireVertexPositions();

  std::ofstream out(outputPath);
  if (!out.is_open()) {
    std::cerr << "Could not open output file: " << outputPath << std::endl;
    return EXIT_FAILURE;
  }

  if (fieldType == "boundary") {
    geometry->requireHalfedgeVectorsInVertex();

    // "Middle of the boundary (opening side)": the boundary vertex with the
    // greatest height, i.e. the crown/apex of the opening's arch profile.
    Vertex middleVertex;
    double bestHeight = -std::numeric_limits<double>::infinity();
    for (Vertex v : mesh->vertices()) {
      if (v.isBoundary()) {
        double h = geometry->vertexPositions[v].y;
        if (h > bestHeight) {
          bestHeight = h;
          middleVertex = v;
        }
      }
    }
    if (middleVertex == Vertex()) {
      std::cerr << "Mesh has no boundary vertices" << std::endl;
      return EXIT_FAILURE;
    }

    Vector2 dir = unit(boundaryNormalDirection(*geometry, middleVertex));
    Vector3 worldDir =
        dir.x * geometry->vertexTangentBasis[middleVertex][0] + dir.y * geometry->vertexTangentBasis[middleVertex][1];
    std::cout << "Middle-of-boundary vertex at height " << bestHeight << ", position "
              << geometry->vertexPositions[middleVertex] << ", direction " << worldDir << std::endl;

    // Copy this single constant world-space direction to every vertex.
    for (size_t i = 0; i < mesh->nVertices(); i++) {
      out << worldDir.x << " " << worldDir.y << " " << worldDir.z << "\n";
    }
  } else {
    VertexData<Vector2> dirField(*mesh); // single (non-doubled) direction per vertex

    if (fieldType == "curvature") {
      // Power representation (angle doubled), nSym = 2. Undo the doubling
      // below before writing out.
      VertexData<Vector2> powerField = computeCurvatureAlignedVertexDirectionField(*geometry, 2);
      for (Vertex v : mesh->vertices()) {
        std::complex<double> z(powerField[v].x, powerField[v].y);
        std::complex<double> halved = std::sqrt(z);
        dirField[v] = unit(Vector2{real(halved), imag(halved)});
      }
    } else if (fieldType == "boundary_smooth") {
      VertexData<Vector2> powerField = computeSmoothestBoundaryAlignedVertexDirectionField(*geometry, 2);
      for (Vertex v : mesh->vertices()) {
        std::complex<double> z(powerField[v].x, powerField[v].y);
        std::complex<double> halved = std::sqrt(z);
        dirField[v] = unit(Vector2{real(halved), imag(halved)});
      }
    } else if (fieldType == "boundary_transport") {
      geometry->requireHalfedgeVectorsInVertex();

      std::vector<std::tuple<Vertex, Vector2>> sources;
      for (Vertex v : mesh->vertices()) {
        if (v.isBoundary()) {
          sources.emplace_back(v, boundaryNormalDirection(*geometry, v));
        }
      }
      std::cout << "Transporting from " << sources.size() << " boundary vertices" << std::endl;

      VectorHeatMethodSolver solver(*geometry);
      dirField = solver.transportTangentVectors(sources);
      for (Vertex v : mesh->vertices()) {
        dirField[v] = unit(dirField[v]);
      }
    } else if (fieldType == "anticlastic") {
      // Every vertex is pinned directly to its own tangent-plane projection
      // of world direction (0,1,0) - this trivially includes the anticlastic
      // (Gaussian curvature < 0) and boundary vertices the field was
      // originally asked to fix at (0,1,0), and keeps every other vertex
      // consistent with the same world direction rather than leaving them to
      // be interpolated from a sparse, unevenly-distributed source set
      // (which was drifting up to 90 degrees off near the vault's ridge,
      // far from any anticlastic/boundary source).
      //
      // The only vertices left unconstrained are the ones where (0,1,0) is
      // nearly parallel to the surface normal (the ridge crest and the
      // boundary opening's crown) - there, the projection onto the tangent
      // plane is nearly zero and normalizing it just amplifies noise into an
      // arbitrary direction. Vector-heat-method transport (Sharp et al.)
      // fills those few points in smoothly from their immediate, densely
      // constrained neighbors instead.
      geometry->requireHalfedgeVectorsInVertex();

      const Vector3 targetWorld{0.0, 1.0, 0.0};
      std::vector<std::tuple<Vertex, Vector2>> sources;
      int nSkippedDegenerate = 0;

      for (Vertex v : mesh->vertices()) {
        double px = dot(targetWorld, geometry->vertexTangentBasis[v][0]);
        double py = dot(targetWorld, geometry->vertexTangentBasis[v][1]);
        if (px * px + py * py < 1e-10) { // truly degenerate only
          nSkippedDegenerate++;
          continue;
        }
        sources.emplace_back(v, unit(Vector2{px, py}));
      }
      std::cout << "Direct (0,1,0)-projected source vertices: " << sources.size() << " / " << mesh->nVertices()
                << " (" << nSkippedDegenerate << " near-degenerate, filled in by transport)" << std::endl;

      VectorHeatMethodSolver solver(*geometry);
      dirField = solver.transportTangentVectors(sources);
      for (Vertex v : mesh->vertices()) {
        dirField[v] = unit(dirField[v]);
      }
    } else if (fieldType == "rotate90") {
      // Rotate each vertex's existing world-space vector by 90 degrees
      // *on the surface*: project onto that vertex's own tangent plane,
      // rotate within the 2D tangent basis (not a single fixed 3D axis,
      // since the tangent plane's orientation varies across a curved
      // surface), then re-embed. This keeps the rotated vector properly
      // tangent everywhere, unlike rotating about one global axis.
      if (existingFieldPath.empty()) {
        std::cerr << "rotate90 requires a 4th argument: path to the existing field file to rotate" << std::endl;
        return EXIT_FAILURE;
      }
      std::ifstream in(existingFieldPath);
      if (!in.is_open()) {
        std::cerr << "Could not open existing field file: " << existingFieldPath << std::endl;
        return EXIT_FAILURE;
      }
      for (Vertex v : mesh->vertices()) {
        double wx, wy, wz;
        in >> wx >> wy >> wz;
        Vector3 worldIn{wx, wy, wz};
        double px = dot(worldIn, geometry->vertexTangentBasis[v][0]);
        double py = dot(worldIn, geometry->vertexTangentBasis[v][1]);
        dirField[v] = unit(Vector2{px, py}.rotate90());
      }
    } else {
      std::cerr << "Unknown field type: " << fieldType << std::endl;
      return EXIT_FAILURE;
    }

    for (Vertex v : mesh->vertices()) {
      Vector2 dir = dirField[v];
      Vector3 worldDir = dir.x * geometry->vertexTangentBasis[v][0] + dir.y * geometry->vertexTangentBasis[v][1];
      out << worldDir.x << " " << worldDir.y << " " << worldDir.z << "\n";
    }
  }

  out.close();

  std::cout << "Wrote direction field to " << outputPath << std::endl;
  return EXIT_SUCCESS;
}
