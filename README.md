# Calculadora PRO de Estrategias de Opciones

Aplicación de escritorio para construir y analizar estrategias de opciones.

Stack: NumPy, Pandas, SciPy, Matplotlib, Tkinter y OpenPyXL.

Incluye:
- hasta 6 patas
- CALL / PUT y compra / venta
- payoff y P&L al vencimiento
- Black-Scholes-Merton
- Delta, Gamma, Vega, Theta y Rho
- break-even aproximado
- probabilidad aproximada de beneficio
- sensibilidad
- plantillas de estrategias
- exportación CSV/Excel

Instalación:

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
# Linux/WSL: source .venv/bin/activate
pip install -r requirements.txt
python main.py
```
