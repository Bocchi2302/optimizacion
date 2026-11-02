# Método MOD

La sección se abre en `/metodo_mod/` desde la página principal. La función
`calcular_mod` y el endpoint están en `blueprints/mod_bp.py`. El HTML y sus
recursos CSS/JS están en `templates/metodo_mod/`; Flask publica los recursos
mediante el blueprint en `/metodo_mod/assets/`.

Se usa módulo euclídeo: `a = b*q + r`, con `0 <= r < abs(b)` y `b != 0`.
Por ejemplo, `10 MOD 3 = 1`, `20 MOD 5 = 0` y `-10 MOD 3 = 2`.
La convención con entradas negativas está explicada en la interfaz.

`POST /metodo_mod/calcular` recibe JSON:

```json
{"dividendo": "10", "divisor": "3"}
```

Devuelve dividendo, divisor, cociente y residuo como cadenas para preservar
la precisión de los enteros en JavaScript, además de los booleanos `divisible`
y `par`. Se aceptan enteros de hasta 200 dígitos, con signo opcional. Datos
inválidos, decimales y divisor cero devuelven HTTP 400 con el campo `error`.

Para ejecutar la aplicación y las pruebas desde la raíz del repositorio:

```sh
python -m pip install -r requirements.txt
python app.py
python -m unittest discover -s tests -v
```
