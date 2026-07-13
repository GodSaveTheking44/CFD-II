"""
Vehicle dynamics point-mass simulation module.
Simulates straight-line acceleration over a 1000m straight using 1D integration.
Models engine power limits, rolling resistance, and tire traction limits
under aerodynamically generated downforce.
"""

import logging
from src.config import (
    CAR_MASS, ENGINE_POWER, GRAVITY, AIR_DENSITY, CAR_FRONTAL_AREA,
    ROLLING_RESISTANCE_COEFF, TIRE_FRICTION_COEFF, STRAIGHT_LENGTH,
    INITIAL_VELOCITY, CAR_BASELINE_DRAG, CAR_BASELINE_DOWNFORCE,
    PHYSICAL_WING_AREA
)

logger = logging.getLogger(__name__)

def simulate_straight_line_performance(cd_x_mode, cl_x_mode, cd_z_mode, cl_z_mode):
    """
    Run 1D straight-line simulation for X-mode and Z-mode configurations
    over a straight track of STRAIGHT_LENGTH.
    
    Args:
        cd_x_mode (float): Drag coefficient in X-mode (from CFD)
        cl_x_mode (float): Lift coefficient in X-mode (from CFD, negative)
        cd_z_mode (float): Drag coefficient in Z-mode (from CFD)
        cl_z_mode (float): Lift coefficient in Z-mode (from CFD, negative)
        
    Returns:
        dict: Simulation stats including top speeds, elapsed times, and deltas
    """
    logger.info("Starting vehicle dynamics simulation...")
    
    # 1. Compute total car drag and lift (downforce) areas (CdA and ClA)
    # Drag Area: CdA_total = Cd_base * Area_base + Cd_wing * Area_wing
    cda_x = CAR_BASELINE_DRAG * CAR_FRONTAL_AREA + cd_x_mode * PHYSICAL_WING_AREA
    cda_z = CAR_BASELINE_DRAG * CAR_FRONTAL_AREA + cd_z_mode * PHYSICAL_WING_AREA
    
    # Downforce Area (CFD Cl is negative, so -Cl is positive downforce area)
    # ClA_total = Cl_base * Area_base - Cl_wing * Area_wing
    cla_x = CAR_BASELINE_DOWNFORCE * CAR_FRONTAL_AREA - cl_x_mode * PHYSICAL_WING_AREA
    cla_z = CAR_BASELINE_DOWNFORCE * CAR_FRONTAL_AREA - cl_z_mode * PHYSICAL_WING_AREA
    
    logger.debug("X-mode CdA = %.4f m^2, ClA (downforce) = %.4f m^2", cda_x, cla_x)
    logger.debug("Z-mode CdA = %.4f m^2, ClA (downforce) = %.4f m^2", cda_z, cla_z)
    
    def simulate_run(cda, cla):
        elapsed_time = 0.0
        distance = 0.0
        velocity = INITIAL_VELOCITY
        time_step = 0.01  # Integration step in seconds
        
        while distance < STRAIGHT_LENGTH:
            # 1. Aerodynamic drag force
            drag_force = 0.5 * AIR_DENSITY * (velocity ** 2) * cda
            
            # 2. Downforce (vertical downward force)
            downforce = 0.5 * AIR_DENSITY * (velocity ** 2) * cla
            
            # 3. Rolling resistance force
            rolling_resistance = ROLLING_RESISTANCE_COEFF * CAR_MASS * GRAVITY
            
            # 4. Engine traction limits
            # Maximum friction force tire can transmit to road
            tire_traction_limit = TIRE_FRICTION_COEFF * (CAR_MASS * GRAVITY + downforce)
            
            # Power limit force (F = Power / Velocity)
            # Avoid divide by zero at zero velocity
            if velocity > 1.0:
                engine_force = ENGINE_POWER / velocity
            else:
                engine_force = ENGINE_POWER
                
            # Actual driving force is the minimum of powertrain force and grip limit
            tractive_force = min(engine_force, tire_traction_limit)
            
            # Net forward force
            net_force = tractive_force - drag_force - rolling_resistance
            
            # Acceleration (F=ma)
            acceleration = net_force / CAR_MASS
            
            # Update state variables using Euler integration
            velocity += acceleration * time_step
            distance += velocity * time_step
            elapsed_time += time_step
            
        return elapsed_time, velocity * 3.6  # time in seconds, speed in km/h
        
    time_x, top_speed_x = simulate_run(cda_x, cla_x)
    time_z, top_speed_z = simulate_run(cda_z, cla_z)
    
    time_delta = time_z - time_x
    speed_delta = top_speed_x - top_speed_z
    
    logger.info("Vehicle simulation completed: Time saved = %.3fs, Top speed gain = %.2f km/h", time_delta, speed_delta)
    
    return {
        "x_mode": {"time": time_x, "top_speed": top_speed_x},
        "z_mode": {"time": time_z, "top_speed": top_speed_z},
        "time_delta": time_delta,
        "speed_delta": speed_delta
    }
