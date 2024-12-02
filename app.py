from flask import Flask, request, jsonify, render_template
from datetime import datetime
import firebase_admin
from firebase_admin import credentials, db
import random

# Inicializar Firebase
cred = credentials.Certificate("sensorhumedad-66c30-firebase-adminsdk-gbulx-94739477ef.json")  # Reemplaza con tu archivo JSON
firebase_admin.initialize_app(cred, {
    'databaseURL': 'https://sensorhumedad-66c30-default-rtdb.firebaseio.com/'  # Reemplaza con la URL de tu Realtime Database
})

# Crear la aplicación Flask
app = Flask(__name__)

# Identificador del sensor
ID_SENSOR = "SVC0425"

# Datos de humedad ideales por cultivo y estación
cultivos = {
    "Arroz": {"Invierno": (70, 80), "Primavera": (65, 75), "Verano": (60, 70), "Otoño": (70, 80)},
    "Lechuga": {"Invierno": (35, 40), "Primavera": (30, 35), "Verano": (35, 40), "Otoño": (30, 35)},
    "Tomate": {"Invierno": (55, 60), "Primavera": (50, 55), "Verano": (50, 60), "Otoño": (55, 60)},
    "Maiz": {"Invierno": (40, 50), "Primavera": (45, 55), "Verano": (50, 60), "Otoño": (40, 50)},
    "Papa": {"Invierno": (60, 70), "Primavera": (50, 60), "Verano": (55, 65), "Otoño": (50, 60)}
}

# Función para seleccionar una estación aleatoria
def obtener_estacion_aleatoria():
    return random.choice(["Invierno", "Primavera", "Verano", "Otoño"])

# Simulador del sensor
def simular_sensor():
    cultivo = random.choice(list(cultivos.keys()))
    estacion = obtener_estacion_aleatoria()
    rango_humedad = cultivos[cultivo][estacion]

    if random.random() < 0.5:
        humedad = random.uniform(0, rango_humedad[0] - 5)
    else:
        humedad = random.uniform(rango_humedad[0], rango_humedad[1])

    humedad = round(humedad, 2)
    necesita_riego = humedad < rango_humedad[0]

    return {
        "cultivo": cultivo,
        "valor": humedad,
        "estacion": estacion,
        "necesita_riego": necesita_riego,
        "tipo_cultivo": cultivo  # Agregar campo para diferenciar cultivos
    }

# Ruta para generar datos automáticamente
@app.route('/api/generar-datos', methods=['POST'])
def generar_datos():
    try:
        # Simular datos del sensor
        datos = simular_sensor()

        # Guardar datos en Firebase
        datos["idsensor"] = ID_SENSOR  # Agregar ID del sensor
        datos["fecha"] = datetime.now().strftime("%Y-%m-%d")
        datos["hora"] = datetime.now().strftime("%H:%M:%S")
        ref = db.reference('sensores')
        ref.push(datos)

        return jsonify({
            "mensaje": "Datos generados y enviados correctamente",
            "datos": datos
        }), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/')
def home():
    return render_template('index.html')

# Ruta para recibir datos del sensor
@app.route('/api/sensor', methods=['POST', 'GET'])
def sensor():
    if request.method == 'POST':
        try:
            data = request.json
            cultivo = data.get("cultivo")
            valor = data.get("valor")
            estacion = data.get("estacion")
            necesita_riego = data.get("necesita_riego")
            tipo_cultivo = data.get("tipo_cultivo")

            if not cultivo or valor is None or not estacion or necesita_riego is None or not tipo_cultivo:
                return jsonify({"error": "Datos incompletos"}), 400

            fecha_actual = datetime.now().strftime("%Y-%m-%d")
            hora_actual = datetime.now().strftime("%H:%M:%S")

            registro = {
                "fecha": fecha_actual,
                "hora": hora_actual,
                "idsensor": ID_SENSOR,
                "valor": valor,
                "cultivo": cultivo,
                "estacion": estacion,
                "necesita_riego": necesita_riego,
                "tipo_cultivo": tipo_cultivo 
            }

            ref = db.reference('sensores')
            ref.push(registro)

            return jsonify({
                "mensaje": "Datos recibidos correctamente",
                "registro": registro
            }), 200

        except Exception as e:
            return jsonify({"error": str(e)}), 500

    elif request.method == 'GET':
        try:
            idsensor = request.args.get('idsensor')
            fecha = request.args.get('fecha')
            cultivo = request.args.get('cultivo')  # Nuevo parámetro para filtrar por cultivo

            # Verificar si faltan parámetros
            if not idsensor or not fecha or not cultivo:
                return jsonify({"error": "Faltan parámetros: idsensor, fecha o cultivo"}), 400

            ref = db.reference('sensores')
            datos = ref.order_by_child('idsensor').equal_to(idsensor).get()

            if datos is None:
                return jsonify({"error": "No se encontraron datos para el sensor especificado."}), 404

            # Filtrar datos por fecha y cultivo
            resultados = [
                v for v in datos.values()
                if v['fecha'] == fecha and v['cultivo'] == cultivo
            ]

            if not resultados:
                return jsonify({"error": "No se encontraron registros para los criterios especificados."}), 404

            return jsonify(resultados), 200

        except Exception as e:
            return jsonify({"error": str(e)}), 500

# Ruta para obtener la lista de sensores únicos
@app.route('/api/sensores', methods=['GET'])
def obtener_sensores():
    try:
        ref = db.reference('sensores')
        datos = ref.get()

        if datos is None:
            return jsonify({"error": "No se encontraron datos en la base de datos."}), 404

        # Extraer IDs de sensores únicos
        sensores = {v['idsensor'] for v in datos.values()}

        return jsonify(list(sensores)), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Ruta para obtener las fechas disponibles de un sensor
@app.route('/api/fechas', methods=['GET'])
def obtener_fechas():
    try:
        idsensor = request.args.get('idsensor')
        if not idsensor:
            return jsonify({"error": "ID del Sensor no proporcionado"}), 400

        # Recuperar datos de Firebase relacionados con el ID del Sensor
        ref = db.reference('sensores')
        registros = ref.order_by_child('idsensor').equal_to(idsensor).get()

        if registros is None:
            return jsonify({"error": "No se encontraron registros para el sensor especificado."}), 404

        # Extraer fechas únicas de los registros
        fechas = list({registro['fecha'] for registro in registros.values()})

        return jsonify(fechas), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/cultivos', methods=['GET'])
def obtener_cultivos():
    try:
        idsensor = request.args.get('idsensor')
        if not idsensor:
            return jsonify({"error": "ID del Sensor no proporcionado"}), 400

        # Recuperar datos de Firebase relacionados con el ID del Sensor
        ref = db.reference('sensores')
        registros = ref.order_by_child('idsensor').equal_to(idsensor).get()

        if registros is None:
            return jsonify({"error": "No se encontraron registros para el sensor especificado."}), 404

        # Extraer cultivos únicos de los registros
        cultivos = list({registro['cultivo'] for registro in registros.values()})

        return jsonify(cultivos), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

def inicializar_datos():
    ref = db.reference('sensores')

    # Recuperar todos los datos existentes
    datos_existentes = ref.get() or {}

    # Contar la cantidad de datos por cultivo
    conteo_por_cultivo = {cultivo: 0 for cultivo in cultivos.keys()}
    for dato in datos_existentes.values():
        cultivo = dato.get('cultivo')
        if cultivo in conteo_por_cultivo:
            conteo_por_cultivo[cultivo] += 1

    # Verificar si algún cultivo tiene menos de 6 datos
    for cultivo, conteo in conteo_por_cultivo.items():
        if conteo < 6:
            print(f"Creando datos para el cultivo: {cultivo} (Faltan {6 - conteo} datos)")
            for _ in range(6 - conteo):
                datos = simular_sensor()
                datos["idsensor"] = ID_SENSOR  # Agregar ID del sensor
                datos["cultivo"] = cultivo  # Asignar el cultivo específico
                datos["fecha"] = datetime.now().strftime("%Y-%m-%d")
                datos["hora"] = datetime.now().strftime("%H:%M:%S")
                ref.push(datos)

    print("Inicialización completada: Datos generados para los cultivos.")

# Iniciar la aplicación Flask
if __name__ == '__main__':
    inicializar_datos()
    app.run(debug=True)