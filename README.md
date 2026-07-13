# F1 Active Aero Rear Wing Trade-off Study (2026 Regulations)

An automated engineering pipeline combining a parametric Multi-Element CFD sweep in **OpenFOAM** (RANS $k$-$\omega$ SST) with a **1D Point-Mass Vehicle Dynamics Model** to quantify the aerodynamic and performance differences between high-downforce **Z-mode** and low-drag **X-mode** configurations.

---

## Project Architecture

This project is refactored to follow professional software development conventions. All core business, mathematical, execution, and parsing concerns are segregated into a structured `src` package.

```text
├── Dockerfile                  # Container environment for OpenFOAM + Python
├── README.md                   # Setup guide and architecture overview
├── generate_geometry.py        # CLI wrapper to output watertight STL wing files
├── run_sweep.py                # CLI pipeline coordinator (mesh study, sweeps, models)
├── src/                        # Core codebase package
│   ├── __init__.py             # Package declaration
│   ├── config.py               # Centralized physical, geometric & vehicle constants
│   ├── geometry.py             # Airfoil generation, rotation, extrusion & STL triangulation
│   ├── openfoam.py             # Shell wrapper automating case initialization and OpenFOAM execution
│   ├── parser.py               # Robust VTK, XY, and force coefficient file parsers
│   ├── vehicle_dynamics.py     # 1D straight-line performance simulation model
│   ├── plotting.py             # Matplotlib plotting procedures (presentation layer)
│   └── report.py               # Markdown report compiler
├── openfoam_template/          # Base template files copied for each simulation case
│   ├── 0.orig/                 # Velocity, pressure, and turbulence boundary fields
│   ├── constant/               # Viscosity and turbulence model selection
│   └── system/                 # Meshing (snappy), solver (simpleFoam), and sampling dicts
└── tests/                      # Unit test suites
    └── test_refactored_modules.py # Geometry, math, rotation, and parser safety tests
```

---

## Setup & Execution

### Option 1: Running in Docker (Recommended)
Because compiling OpenFOAM and configuring Python dependencies is platform-dependent, a Docker environment is provided.

1. **Build the Docker Image**:
   ```bash
   docker build -t active-aero .
   ```

2. **Execute the Sweep Pipeline**:
   Mount a local volume to map the container output directory `./output` to your host workspace:
   ```bash
   docker run --rm -v "${PWD}/output:/app/output" active-aero
   ```

3. **Output Files**:
   Once execution finishes, look inside the generated `./output/` directory for:
   - `report.md`: The complete engineering report containing mesh independence checks, polar sweeps, and performance summaries.
   - `polar_curve.png`: Aerodynamic polar sweep ($C_l$ vs. $C_d$).
   - `mesh_independence.png`: Lift and drag convergence curves.
   - `cp_distribution.png`: Surface pressure distribution ($C_p$) comparing Z-mode and X-mode.
   - `wake_velocity.png`: Horizontal wake velocity profiles at $x=1.5$m.

### Option 2: Running Geometry & Unit Tests Locally
If you have Python 3 and NumPy installed, you can generate geometries and execute tests without launching OpenFOAM:

1. **Generate a Specific STL Wing**:
   ```bash
   # Generate X-mode (t=0.0) wing
   python3 generate_geometry.py -t 0.0 -o output/wing_x_mode.stl -s 0.2
   ```

2. **Execute the Unit Test Suite**:
   ```bash
   python3 -m unittest tests/test_refactored_modules.py
   ```

---

## Key Technical Decisions & Methodologies

### 1. 2D snappyHexMesh Slicing Strategy
OpenFOAM's `snappyHexMesh` is natively a 3D octree-based mesh generator. Performing true 2D snaps on geometries is typically error-prone and unstable.
* **Our Workaround**: We generate a thin 2.5D background blockMesh and a fully extruded 3D wing STL. `snappyHexMesh` refines and snaps this 3D domain. Then, `extrudeMesh` takes a single 2D face patch (the front plane) and extrudes it by exactly one layer in Z. Finally, `changeDictionary` updates the patch type of the front and back planes to `empty`.
* **Impact**: Runtimes drop from hours (for a 3D half-span mesh) to less than 1 minute per run, permitting a comprehensive 5-angle sweep and a 3-grid mesh convergence study.

### 2. Coupled Aerodynamic-Powertrain Vehicle Model
Most CFD studies stop at reporting $C_l$ and $C_d$ coefficients. This project features a 1D vehicle dynamics model integrating equations of motion over a 1000-meter straight:
$$m \frac{dv}{dt} = F_{\text{tractive}}(v) - F_{\text{drag}}(v) - F_{\text{rolling}}$$
* **Traction Limit**: $F_{\text{traction}} = \mu (m g + F_{\text{downforce}})$. Downforce scales quadratically with speed: $F_{\text{downforce}} = \frac{1}{2} \rho v^2 C_l A_{\text{total}}$.
* **Powertrain Limit**: $F_{\text{power}} = P_{\text{engine}} / v$.
* **Tractive Force**: $F_{\text{tractive}} = \min(F_{\text{power}}, F_{\text{traction}})$.

This model links CFD results directly to track performance metrics (e.g., straight-line elapsed time and top speed).

---

## Engineering Trade-offs

1. **2D RANS vs. 3D Induced Drag**:
   2D simulations assume an infinite wing span. They do not model wingtip vortices or downwash, which alter the local angle of attack and introduce induced drag. While 2D captures the sectional airfoil efficiency (profile drag/lift), a full 3D simulation with endplates is necessary to capture absolute aerodynamic coefficients.
2. **Steady-state RANS vs. Transient DES**:
   Steady-state RANS (`simpleFoam`) with a $k$-$\omega$ SST model solves for time-averaged flow fields. It is highly efficient but cannot capture highly transient vortex shedding in stalled elements. 

---

## Verification & Robustness

- **Mesh Independence**: The automated convergence study monitors $C_l$ and $C_d$ changes across Coarse, Medium, and Fine meshes to confirm asymptotic grid convergence.
- **Safety in Parsing**: Parsers do not fail silently or crash the pipeline when files are corrupt or missing. They raise explicit logging warnings and return safe configurations.
- **Constant Management**: Configurations and physical constants are locked in `src/config.py` to prevent structural drift.
