# MATLAB Files

MATLAB scripts for modeling, transfer function derivation, controller design, observer design and simulations.
# MATLAB Design Workflow

The scripts are executed sequentially because variables generated in each stage are used by subsequent stages.

Execution order:

1. 01_Calculo_Resistencias_Hidraulicas.mlx
   - Hydraulic parameter calculation.

2. 02_TF_Tanques.mlx
   - Transfer function derivation.

3. 03_Control_Tanques.mlx
   - PI and PD controller design.

4. 04_Espacio_Estados_Observador.mlx
   - State-space representation and observer design.

5. 05_Servo_Con_Observador.mlx
   - Observer-based servosystem implementation.

Important:
Run the scripts in the specified order because they share workspace variables.
