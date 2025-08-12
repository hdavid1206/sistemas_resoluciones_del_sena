from flask import Flask, render_template, request, redirect, url_for, flash, send_file, jsonify, session
import pandas as pd
import os
from werkzeug.utils import secure_filename
from database import DatabaseManager
from document_generator import DocumentGenerator
import json
import zipfile
from datetime import datetime

app = Flask(__name__)
app.secret_key = 'sena_centro_minero_2023_resoluciones'

# Configuración
UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'xlsx', 'xls', 'csv'}

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max

# Configuración de base de datos MySQL
DB_CONFIG = {
    'host': 'localhost',
    'database': 'sena_bienestar',
    'user': 'root',
    'password': ''  # CAMBIAR POR TU CONTRASEÑA
}

# Asegurar que existan los directorios necesarios
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs('generated', exist_ok=True)

# Inicializar base de datos y generador de documentos
try:
    db = DatabaseManager(**DB_CONFIG)
    doc_generator = DocumentGenerator()
    print("✅ Conexión a MySQL exitosa")
except Exception as e:
    print(f"❌ Error al conectar con MySQL: {e}")
    db = None
    doc_generator = None

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/')
def index():
    """Página principal"""
    return render_template('index.html')

@app.route('/upload', methods=['GET', 'POST'])
def upload_file():
    """Subir archivo con listado de aprendices"""
    if request.method == 'POST':
        if 'file' not in request.files:
            flash('No se seleccionó archivo', 'error')
            return redirect(request.url)
        
        file = request.files['file']
        tipo_resolucion = request.form.get('tipo_resolucion')
        
        if file.filename == '':
            flash('No se seleccionó archivo', 'error')
            return redirect(request.url)
        
        if not tipo_resolucion:
            flash('Debe seleccionar el tipo de resolución', 'error')
            return redirect(request.url)
        
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)
            
            # Procesar archivo
            try:
                if filename.endswith('.csv'):
                    df = pd.read_csv(filepath, encoding='utf-8')
                else:
                    df = pd.read_excel(filepath)
                
                # Validar columnas requeridas
                required_columns = ['numero_documento', 'tipo_documento', 'nombres', 'apellidos', 'programa', 'ficha']
                missing_columns = [col for col in required_columns if col not in df.columns]
                
                if missing_columns:
                    flash(f'Faltan columnas requeridas: {", ".join(missing_columns)}', 'error')
                    return redirect(request.url)
                
                # Limpiar datos
                df = df.dropna(subset=['numero_documento', 'nombres', 'apellidos'])
                
                # Registrar carga masiva
                if db:
                    carga_id = db.insert_carga_masiva(filename, tipo_resolucion, len(df))
                
                # Procesar datos
                processed_data = []
                errors = []
                exitosos = 0
                fallidos = 0
                
                for index, row in df.iterrows():
                    try:
                        # Validar y limpiar datos
                        aprendiz_data = {
                            'numero_documento': str(row['numero_documento']).strip(),
                            'tipo_documento': str(row['tipo_documento']).strip() if not pd.isna(row['tipo_documento']) else 'CC',
                            'nombres': str(row['nombres']).strip().upper(),
                            'apellidos': str(row['apellidos']).strip().upper(),
                            'programa': str(row['programa']).strip(),
                            'ficha': str(row['ficha']).strip(),
                            'fecha_nacimiento': str(row['fecha_nacimiento']) if 'fecha_nacimiento' in row and not pd.isna(row['fecha_nacimiento']) else None,
                            'telefono': str(row['telefono']) if 'telefono' in row and not pd.isna(row['telefono']) else None,
                            'email': str(row['email']) if 'email' in row and not pd.isna(row['email']) else None
                        }
                        
                        # Insertar en base de datos
                        if db:
                            aprendiz_id = db.insert_aprendiz(aprendiz_data)
                            if aprendiz_id:
                                processed_data.append({**aprendiz_data, 'id': aprendiz_id, 'status': 'nuevo'})
                                exitosos += 1
                            else:
                                processed_data.append({**aprendiz_data, 'status': 'existente'})
                                exitosos += 1
                        else:
                            processed_data.append({**aprendiz_data, 'status': 'nuevo'})
                            exitosos += 1
                    
                    except Exception as e:
                        errors.append(f'Fila {index + 2}: {str(e)}')
                        fallidos += 1
                
                # Actualizar carga masiva
                if db and 'carga_id' in locals():
                    db.update_carga_masiva(carga_id, exitosos, fallidos)
                
                # Guardar datos en sesión
                session['processed_data'] = processed_data
                session['tipo_resolucion'] = tipo_resolucion
                session['errors'] = errors
                
                flash(f'Archivo procesado exitosamente: {exitosos} registros cargados', 'success')
                if errors:
                    flash(f'Se encontraron {len(errors)} errores', 'warning')
                
                return redirect(url_for('validate_data'))
                
            except Exception as e:
                flash(f'Error al procesar archivo: {str(e)}', 'error')
                return redirect(request.url)
        
        flash('Tipo de archivo no permitido. Use Excel (.xlsx, .xls) o CSV (.csv)', 'error')
        return redirect(request.url)
    
    return render_template('upload.html')

@app.route('/validate')
def validate_data():
    """Validar datos cargados"""
    processed_data = session.get('processed_data', [])
    tipo_resolucion = session.get('tipo_resolucion', '')
    errors = session.get('errors', [])
    
    if not processed_data:
        flash('No hay datos para validar. Cargue un archivo primero.', 'error')
        return redirect(url_for('upload_file'))
    
    return render_template('validate.html', 
                         data=processed_data, 
                         tipo_resolucion=tipo_resolucion,
                         errors=errors)

@app.route('/generate', methods=['GET', 'POST'])
def generate_resolutions():
    """Generar resoluciones"""
    if request.method == 'POST':
        aprendices_seleccionados = request.form.getlist('aprendices')
        numero_inicial = int(request.form.get('numero_inicial', 1))
        prefijo = request.form.get('prefijo', '15-')
        
        # Obtener tipo de resolución de la sesión
        tipo_resolucion = session.get('tipo_resolucion')
        
        if not tipo_resolucion:
            flash('No se encontró el tipo de resolución. Cargue un archivo primero.', 'error')
            return redirect(url_for('upload_file'))
        
        if not aprendices_seleccionados:
            flash('Debe seleccionar al menos un aprendiz', 'error')
            return redirect(request.url)
        
        # Obtener plantilla específica para el tipo de resolución
        if db:
            plantillas = db.get_plantillas_by_tipo(tipo_resolucion)
        else:
            plantillas = []
        
        if not plantillas:
            flash(f'No se encontró plantilla para el tipo de resolución: {tipo_resolucion}', 'error')
            return redirect(request.url)
        
        plantilla = plantillas[0]  # Usar la primera plantilla del tipo
        plantilla_data = {
            'id': plantilla[0],
            'nombre': plantilla[1],
            'tipo': plantilla[2],
            'descripcion': plantilla[3] if len(plantilla) > 3 else '',
            'contenido': plantilla[4] if len(plantilla) > 4 else plantilla[3],
            'variables': plantilla[5] if len(plantilla) > 5 else plantilla[4]
        }
        
        # Obtener datos de aprendices seleccionados
        processed_data = session.get('processed_data', [])
        aprendices_data = []
        
        for aprendiz in processed_data:
            if str(aprendiz.get('id', '')) in aprendices_seleccionados or aprendiz['numero_documento'] in aprendices_seleccionados:
                aprendices_data.append(aprendiz)
        
        if not aprendices_data:
            flash('No se encontraron los aprendices seleccionados', 'error')
            return redirect(request.url)
        
        # Generar resoluciones
        try:
            generated_files = []
            
            for i, aprendiz in enumerate(aprendices_data, numero_inicial):
                # Generar número de resolución único
                numero_resolucion = f"{prefijo}{i:05d}"
                
                try:
                    filepath = doc_generator.generate_resolution(aprendiz, plantilla_data, numero_resolucion)
                    
                    # Guardar resolución en base de datos
                    if db and aprendiz.get('id'):
                        db.insert_resolucion(numero_resolucion, tipo_resolucion, aprendiz['id'], 
                                           plantilla_data['contenido'], filepath)
                    
                    generated_files.append({
                        'aprendiz': f"{aprendiz['nombres']} {aprendiz['apellidos']}",
                        'numero_documento': aprendiz['numero_documento'],
                        'numero_resolucion': numero_resolucion,
                        'filepath': filepath,
                        'status': 'success'
                    })
                    
                except Exception as e:
                    generated_files.append({
                        'aprendiz': f"{aprendiz['nombres']} {aprendiz['apellidos']}",
                        'numero_documento': aprendiz['numero_documento'],
                        'numero_resolucion': numero_resolucion,
                        'filepath': None,
                        'status': 'error',
                        'error': str(e)
                    })
            
            # Crear resumen
            summary_file = doc_generator.create_batch_summary(generated_files)
            
            # Guardar resultados en sesión
            session['generated_files'] = generated_files
            session['summary_file'] = summary_file
            
            exitosos = len([f for f in generated_files if f['status'] == 'success'])
            flash(f'Se generaron {exitosos} de {len(generated_files)} resoluciones exitosamente', 'success')
            
            return redirect(url_for('results'))
            
        except Exception as e:
            flash(f'Error al generar resoluciones: {str(e)}', 'error')
            return redirect(request.url)
    
    # GET - Mostrar formulario
    processed_data = session.get('processed_data', [])
    tipo_resolucion = session.get('tipo_resolucion', '')
    
    if not processed_data:
        flash('No hay datos cargados. Cargue un archivo primero.', 'error')
        return redirect(url_for('upload_file'))
    
    # Obtener plantillas para el tipo seleccionado
    if db:
        plantillas = db.get_plantillas_by_tipo(tipo_resolucion)
    else:
        plantillas = []
    
    return render_template('generate.html', 
                         plantillas=plantillas, 
                         aprendices=processed_data,
                         tipo_resolucion=tipo_resolucion)

@app.route('/results')
def results():
    """Mostrar resultados de generación"""
    generated_files = session.get('generated_files', [])
    summary_file = session.get('summary_file', '')
    
    if not generated_files:
        flash('No hay resultados para mostrar', 'error')
        return redirect(url_for('index'))
    
    return render_template('results.html', 
                         generated_files=generated_files,
                         summary_file=summary_file)

@app.route('/download/<filename>')
def download_file(filename):
    """Descargar archivo generado"""
    try:
        return send_file(os.path.join('generated', filename), as_attachment=True)
    except Exception as e:
        flash(f'Error al descargar archivo: {str(e)}', 'error')
        return redirect(url_for('index'))

@app.route('/download-multiple', methods=['POST'])
def download_multiple():
    """Descargar múltiples archivos en ZIP"""
    files = request.form.getlist('files')
    if not files:
        flash('No se seleccionaron archivos', 'error')
        return redirect(url_for('results'))
    
    try:
        # Crear archivo ZIP
        zip_filename = f"resoluciones_{datetime.now().strftime('%Y%m%d_%H%M%S')}.zip"
        zip_path = os.path.join('generated', zip_filename)
        
        with zipfile.ZipFile(zip_path, 'w') as zipf:
            for file_path in files:
                if os.path.exists(file_path):
                    arcname = os.path.basename(file_path)
                    zipf.write(file_path, arcname)
        
        return send_file(zip_path, as_attachment=True)
        
    except Exception as e:
        flash(f'Error al crear archivo ZIP: {str(e)}', 'error')
        return redirect(url_for('results'))

@app.errorhandler(404)
def not_found_error(error):
    """Manejar error 404"""
    return render_template('error.html', 
                         error_code=404, 
                         error_message="Página no encontrada"), 404

@app.errorhandler(500)
def internal_error(error):
    """Manejar error 500"""
    return render_template('error.html', 
                         error_code=500, 
                         error_message="Error interno del servidor"), 500

@app.context_processor
def inject_globals():
    """Inyectar variables globales en templates"""
    return {
        'app_name': 'Sistema de Resoluciones SENA',
        'centro_name': 'Centro Minero',
        'regional_name': 'SENA Regional Boyacá'
    }

if __name__ == '__main__':
    # Verificar conexión a MySQL al iniciar
    if db is None:
        print("=" * 50)
        print("❌ ERROR: No se pudo conectar a MySQL")
        print("Verifique que:")
        print("1. MySQL esté instalado y ejecutándose")
        print("2. Las credenciales sean correctas")
        print("3. La base de datos 'sena_bienestar' exista")
        print("=" * 50)
    else:
        print("=" * 50)
        print("✅ Sistema iniciado correctamente")
        print("✅ Conexión a MySQL establecida")
        print("✅ Base de datos y tablas creadas")
        print("✅ Plantillas por defecto cargadas")
        print("📱 Accede al sistema en: http://localhost:5000")
        print("=" * 50)
    
    app.run(debug=True, host='0.0.0.0', port=5000)