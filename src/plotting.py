"""
Plotting and visualization module.
Encapsulates all Matplotlib logic to generate clean engineering plots
for the polar curve, mesh convergence, Cp distribution, and wake deficit.
"""

import os
import logging
import matplotlib
matplotlib.use('Agg')  # Headless plotting for server/container environments
import matplotlib.pyplot as plt
import numpy as np

logger = logging.getLogger(__name__)

def plot_polar_curve(sweep_results, output_dir):
    """
    Generate and save the Cl vs Cd aerodynamic polar sweep curve.
    
    Args:
        sweep_results (list): List of dicts containing sweep results
        output_dir (str): Directory where the figure will be saved
    """
    logger.info("Generating aerodynamic polar sweep plot...")
    plt.figure(figsize=(8, 6))
    
    cds = [r["Cd"] for r in sweep_results]
    cls = [r["Cl"] for r in sweep_results]
    ts = [r["t"] for r in sweep_results]
    
    plt.plot(cds, cls, 'o-', color='#1f77b4', linewidth=2.5, markersize=8)
    
    for i, t_val in enumerate(ts):
        label = "t=0.00 (X-mode)" if t_val == 0.0 else ("t=1.00 (Z-mode)" if t_val == 1.0 else f"t={t_val:.2f}")
        plt.annotate(
            label, 
            (cds[i], cls[i]), 
            textcoords="offset points", 
            xytext=(10, -5), 
            ha='left', 
            fontsize=9,
            fontweight='semibold'
        )
        
    plt.xlabel('Drag Coefficient ($C_d$)', fontsize=12)
    plt.ylabel('Lift Coefficient ($C_l$)', fontsize=12)
    plt.title('Aerodynamic Polar Curve: F1 Active Rear Wing Sweep', fontsize=14, fontweight='bold')
    plt.grid(True, linestyle='--', alpha=0.6)
    plt.tight_layout()
    
    out_path = os.path.join(output_dir, "polar_curve.png")
    plt.savefig(out_path, dpi=150)
    plt.close()
    logger.debug("Aerodynamic polar plot saved to %s", out_path)

def plot_mesh_convergence(mesh_study, output_dir):
    """
    Generate and save the mesh independence check plots.
    
    Args:
        mesh_study (dict): Dictionary containing mesh convergence data for t=0.0 and t=1.0
        output_dir (str): Directory where the figure will be saved
    """
    logger.info("Generating mesh independence convergence plots...")
    plt.figure(figsize=(10, 5))
    
    # Subplot 1: Drag Coefficient convergence
    plt.subplot(1, 2, 1)
    for t_val, color, mode in [(0.0, '#2ca02c', 'X-mode'), (1.0, '#d62728', 'Z-mode')]:
        study = mesh_study[t_val]
        if not study:
            continue
        cells = [s["cells"] for s in study]
        cds_study = [s["Cd"] for s in study]
        # Sort by cell count for clean line plotting
        sort_idx = np.argsort(cells)
        plt.plot(np.array(cells)[sort_idx], np.array(cds_study)[sort_idx], 's--', color=color, label=mode, linewidth=1.5)
        
    plt.xlabel('Cell Count', fontsize=10)
    plt.ylabel('Drag Coefficient ($C_d$)', fontsize=10)
    plt.title('Drag Mesh Independence', fontsize=11, fontweight='bold')
    plt.grid(True, linestyle='--', alpha=0.5)
    plt.legend()
    
    # Subplot 2: Lift Coefficient convergence
    plt.subplot(1, 2, 2)
    for t_val, color, mode in [(0.0, '#2ca02c', 'X-mode'), (1.0, '#d62728', 'Z-mode')]:
        study = mesh_study[t_val]
        if not study:
            continue
        cells = [s["cells"] for s in study]
        cls_study = [s["Cl"] for s in study]
        sort_idx = np.argsort(cells)
        plt.plot(np.array(cells)[sort_idx], np.array(cls_study)[sort_idx], 'o--', color=color, label=mode, linewidth=1.5)
        
    plt.xlabel('Cell Count', fontsize=10)
    plt.ylabel('Lift Coefficient ($C_l$)', fontsize=10)
    plt.title('Lift Mesh Independence', fontsize=11, fontweight='bold')
    plt.grid(True, linestyle='--', alpha=0.5)
    plt.legend()
    
    plt.tight_layout()
    out_path = os.path.join(output_dir, "mesh_independence.png")
    plt.savefig(out_path, dpi=150)
    plt.close()
    logger.debug("Mesh convergence plots saved to %s", out_path)

def plot_pressure_distribution(cp_data_x, cp_data_z, output_dir):
    """
    Generate and save the surface pressure coefficient (Cp) distribution comparison.
    
    Args:
        cp_data_x (tuple): (x_coords, y_coords, cp_values) for X-mode, or None
        cp_data_z (tuple): (x_coords, y_coords, cp_values) for Z-mode, or None
        output_dir (str): Directory where the figure will be saved
    """
    logger.info("Generating Cp surface pressure distribution plot...")
    plt.figure(figsize=(8, 5))
    
    if cp_data_x is not None:
        x_cp, _, cp_vals = cp_data_x
        plt.scatter(x_cp, cp_vals, s=8, color='#2ca02c', label='X-mode (t=0.00)', alpha=0.8)
        
    if cp_data_z is not None:
        x_cp, _, cp_vals = cp_data_z
        plt.scatter(x_cp, cp_vals, s=8, color='#d62728', label='Z-mode (t=1.00)', alpha=0.8)
        
    # Invert Y-axis for Cp plots: negative pressure (suction) is traditionally up
    plt.gca().invert_yaxis()
    plt.xlabel('Chord Coordinate ($x$ in m)', fontsize=12)
    plt.ylabel('Pressure Coefficient ($C_p$)', fontsize=12)
    plt.title('Pressure Coefficient ($C_p$) Surface Distribution', fontsize=14, fontweight='bold')
    plt.grid(True, linestyle='--', alpha=0.6)
    plt.legend()
    plt.tight_layout()
    
    out_path = os.path.join(output_dir, "cp_distribution.png")
    plt.savefig(out_path, dpi=150)
    plt.close()
    logger.debug("Cp distribution plot saved to %s", out_path)

def plot_wake_deficit(wake_data_x, wake_data_z, output_dir):
    """
    Generate and save the normalized wake velocity deficit profile.
    
    Args:
        wake_data_x (tuple): (y_coords, ux_velocities) for X-mode, or None
        wake_data_z (tuple): (y_coords, ux_velocities) for Z-mode, or None
        output_dir (str): Directory where the figure will be saved
    """
    logger.info("Generating wake velocity deficit plot...")
    plt.figure(figsize=(8, 5))
    
    # Inlet/Freestream velocity is 50.0 m/s
    inlet_velocity = 50.0
    
    if wake_data_x is not None:
        ys, uxs = wake_data_x
        plt.plot(uxs / inlet_velocity, ys, color='#2ca02c', linewidth=2.5, label='X-mode (t=0.00)')
        
    if wake_data_z is not None:
        ys, uxs = wake_data_z
        plt.plot(uxs / inlet_velocity, ys, color='#d62728', linewidth=2.5, label='Z-mode (t=1.00)')
        
    plt.axvline(1.0, color='k', linestyle='--', alpha=0.5, label='Freestream ($U/U_\infty = 1.0$)')
    plt.xlabel('Normalized Velocity ($U_x/U_\infty$)', fontsize=12)
    plt.ylabel('Vertical Coordinate $y$ (m)', fontsize=12)
    plt.title('Wake Velocity Deficit Profile ($x = 1.5$m)', fontsize=14, fontweight='bold')
    plt.grid(True, linestyle='--', alpha=0.6)
    plt.legend()
    plt.tight_layout()
    
    out_path = os.path.join(output_dir, "wake_velocity.png")
    plt.savefig(out_path, dpi=150)
    plt.close()
    logger.debug("Wake velocity profile saved to %s", out_path)
