import mysql.connector
from mysql.connector import Error
import os
from datetime import datetime

class DatabaseManager:
    def __init__(self, host='localhost', database='sena_bienestar', user='root', password=''):
        self.host = host
        self.database = database
        self.user = user
        self.password = password
        self.ensure_database_exists()
        self.create_tables()
    
    def ensure_database_exists(self):
        """Crea la base de datos si no existe"""
        try:
            connection = mysql.connector.connect(
                host=self.host,
                user=self.user,
                password=self.password
            )
            cursor = connection.cursor()
            cursor.execute(f"CREATE DATABASE IF NOT EXISTS {self.database} CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
            connection.commit()
            cursor.close()
            connection.close()
            print(f"✅ Base de datos '{self.database}' creada/verificada")
        except Error as e:
            print(f"❌ Error al crear la base de datos: {e}")
    
    def get_connection(self):
        """Obtiene conexión a la base de datos MySQL"""
        try:
            connection = mysql.connector.connect(
                host=self.host,
                database=self.database,
                user=self.user,
                password=self.password,
                charset='utf8mb4'
            )
            return connection
        except Error as e:
            print(f"❌ Error al conectar con MySQL: {e}")
            return None
    
    def create_tables(self):
        """Crea las tablas necesarias en MySQL"""
        connection = self.get_connection()
        if not connection:
            return
            
        cursor = connection.cursor()
        
        try:
            # Tabla de aprendices
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS aprendices (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    numero_documento VARCHAR(20) UNIQUE NOT NULL,
                    tipo_documento VARCHAR(5) NOT NULL,
                    nombres VARCHAR(100) NOT NULL,
                    apellidos VARCHAR(100) NOT NULL,
                    programa VARCHAR(200) NOT NULL,
                    ficha VARCHAR(20) NOT NULL,
                    fecha_nacimiento DATE NULL,
                    telefono VARCHAR(20) NULL,
                    email VARCHAR(100) NULL,
                    estado VARCHAR(20) DEFAULT 'ACTIVO',
                    fecha_registro TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    INDEX idx_numero_documento (numero_documento),
                    INDEX idx_ficha (ficha),
                    INDEX idx_estado (estado)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            ''')
            
            # Tabla de resoluciones
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS resoluciones (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    numero_resolucion VARCHAR(50) UNIQUE NOT NULL,
                    tipo_resolucion VARCHAR(50) NOT NULL,
                    aprendiz_id INT NOT NULL,
                    contenido TEXT NOT NULL,
                    fecha_generacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    estado VARCHAR(20) DEFAULT 'GENERADA',
                    archivo_path VARCHAR(500) NULL,
                    usuario_creacion VARCHAR(100) NULL,
                    observaciones TEXT NULL,
                    FOREIGN KEY (aprendiz_id) REFERENCES aprendices (id) ON DELETE CASCADE,
                    INDEX idx_numero_resolucion (numero_resolucion),
                    INDEX idx_tipo_resolucion (tipo_resolucion),
                    INDEX idx_fecha_generacion (fecha_generacion)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            ''')
            
            # Tabla de plantillas
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS plantillas (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    nombre VARCHAR(200) NOT NULL,
                    tipo VARCHAR(50) NOT NULL,
                    descripcion TEXT NULL,
                    contenido TEXT NOT NULL,
                    variables TEXT NULL,
                    fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    fecha_actualizacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                    activa BOOLEAN DEFAULT TRUE,
                    usuario_creacion VARCHAR(100) NULL,
                    INDEX idx_tipo (tipo),
                    INDEX idx_activa (activa)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            ''')
            
            # Tabla de cargas masivas
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS cargas_masivas (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    nombre_archivo VARCHAR(255) NOT NULL,
                    tipo_resolucion VARCHAR(50) NOT NULL,
                    total_registros INT NOT NULL,
                    registros_exitosos INT DEFAULT 0,
                    registros_fallidos INT DEFAULT 0,
                    fecha_carga TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    usuario_carga VARCHAR(100) NULL,
                    estado VARCHAR(20) DEFAULT 'PROCESANDO',
                    observaciones TEXT NULL,
                    INDEX idx_tipo_resolucion (tipo_resolucion),
                    INDEX idx_fecha_carga (fecha_carga),
                    INDEX idx_estado (estado)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            ''')
            
            connection.commit()
            print("✅ Tablas creadas exitosamente")
            
        except Error as e:
            print(f"❌ Error al crear tablas: {e}")
            connection.rollback()
        finally:
            cursor.close()
            connection.close()
        
        # Insertar plantillas por defecto
        self.insert_default_templates()
    
    def insert_default_templates(self):
        """Inserta plantillas por defecto del SENA"""
        connection = self.get_connection()
        if not connection:
            return
            
        cursor = connection.cursor()
        
        try:
            # Verificar si ya existen plantillas
            cursor.execute('SELECT COUNT(*) FROM plantillas')
            count = cursor.fetchone()[0]
            
            if count == 0:
                plantillas_default = [
                    {
                        'nombre': 'Resolución de Apoyo de Sostenimiento FIC',
                        'tipo': 'APOYO_SOSTENIMIENTO',
                        'descripcion': 'Resolución para otorgar apoyo de sostenimiento del Fondo de la Industria de la Construcción',
                        'contenido': '''ARTÍCULO 1°: Otorgar apoyo de sostenimiento FIC al aprendiz {nombres} {apellidos}, identificado con {tipo_documento} No. {numero_documento}, quien se encuentra matriculado en el programa de formación {programa}, ficha {ficha}, del Centro Minero SENA Regional Boyacá.

ARTÍCULO 2°: El presente apoyo se otorga por el período académico correspondiente al programa de formación matriculado, de conformidad con la normatividad vigente y los recursos presupuestales disponibles.

ARTÍCULO 3°: La presente resolución rige a partir de la fecha de su expedición.''',
                        'variables': 'numero_resolucion,nombres,apellidos,tipo_documento,numero_documento,programa,ficha,ciudad,dia,mes,año'
                    },
                    {
                        'nombre': 'Resolución de Apoyo de Transporte',
                        'tipo': 'TRANSPORTE',
                        'descripcion': 'Resolución para otorgar apoyo de transporte a aprendices',
                        'contenido': '''ARTÍCULO 1°: Otorgar apoyo de transporte al aprendiz {nombres} {apellidos}, identificado con {tipo_documento} No. {numero_documento}, matriculado en el programa {programa}, ficha {ficha}.

ARTÍCULO 2°: El apoyo se otorga para facilitar el desplazamiento desde su lugar de residencia hasta el Centro de Formación y viceversa, durante el período de formación.

ARTÍCULO 3°: La presente resolución rige a partir de la fecha de su expedición.''',
                        'variables': 'numero_resolucion,nombres,apellidos,tipo_documento,numero_documento,programa,ficha'
                    },
                    {
                        'nombre': 'Resolución de Monitoria Académica',
                        'tipo': 'MONITORIA',
                        'descripcion': 'Resolución para designar monitores académicos por excelencia',
                        'contenido': '''ARTÍCULO 1°: Designar como monitor académico al aprendiz {nombres} {apellidos}, identificado con {tipo_documento} No. {numero_documento}, del programa {programa}, ficha {ficha}.

ARTÍCULO 2°: Las actividades de monitoria se desarrollarán bajo la supervisión del Coordinador Académico y tendrán una duración de cuatro (4) meses.

ARTÍCULO 3°: El monitor recibirá un estímulo económico mensual equivalente al 50% del salario mínimo legal vigente.

ARTÍCULO 4°: La presente resolución rige a partir de la fecha de su expedición.''',
                        'variables': 'numero_resolucion,nombres,apellidos,tipo_documento,numero_documento,programa,ficha'
                    }
                ]
                
                for plantilla in plantillas_default:
                    cursor.execute('''
                        INSERT INTO plantillas (nombre, tipo, descripcion, contenido, variables, usuario_creacion)
                        VALUES (%s, %s, %s, %s, %s, %s)
                    ''', (plantilla['nombre'], plantilla['tipo'], plantilla['descripcion'],
                         plantilla['contenido'], plantilla['variables'], 'SISTEMA'))
                
                connection.commit()
                print("✅ Plantillas por defecto insertadas")
                
        except Error as e:
            print(f"❌ Error al insertar plantillas: {e}")
            connection.rollback()
        finally:
            cursor.close()
            connection.close()
    
    def insert_aprendiz(self, datos):
        """Inserta un nuevo aprendiz"""
        connection = self.get_connection()
        if not connection:
            return None
            
        cursor = connection.cursor()
        
        try:
            cursor.execute('''
                INSERT INTO aprendices 
                (numero_documento, tipo_documento, nombres, apellidos, programa, ficha, 
                 fecha_nacimiento, telefono, email)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            ''', (
                datos['numero_documento'], datos['tipo_documento'], 
                datos['nombres'], datos['apellidos'], datos['programa'], 
                datos['ficha'], datos.get('fecha_nacimiento'), 
                datos.get('telefono'), datos.get('email')
            ))
            
            connection.commit()
            aprendiz_id = cursor.lastrowid
            return aprendiz_id
            
        except mysql.connector.IntegrityError:
            return None
        except Error as e:
            print(f"❌ Error al insertar aprendiz: {e}")
            return None
        finally:
            cursor.close()
            connection.close()
    
    def get_plantillas_by_tipo(self, tipo):
        """Obtiene plantillas por tipo específico"""
        connection = self.get_connection()
        if not connection:
            return []
            
        cursor = connection.cursor()
        
        try:
            cursor.execute('SELECT * FROM plantillas WHERE tipo = %s AND activa = TRUE', (tipo,))
            plantillas = cursor.fetchall()
            return plantillas
        except Error as e:
            print(f"❌ Error al obtener plantillas por tipo: {e}")
            return []
        finally:
            cursor.close()
            connection.close()
    
    def insert_carga_masiva(self, nombre_archivo, tipo_resolucion, total_registros, usuario='SISTEMA'):
        """Registra una carga masiva"""
        connection = self.get_connection()
        if not connection:
            return None
            
        cursor = connection.cursor()
        
        try:
            cursor.execute('''
                INSERT INTO cargas_masivas 
                (nombre_archivo, tipo_resolucion, total_registros, usuario_carga)
                VALUES (%s, %s, %s, %s)
            ''', (nombre_archivo, tipo_resolucion, total_registros, usuario))
            
            connection.commit()
            carga_id = cursor.lastrowid
            return carga_id
            
        except Error as e:
            print(f"❌ Error al registrar carga masiva: {e}")
            return None
        finally:
            cursor.close()
            connection.close()
    
    def update_carga_masiva(self, carga_id, exitosos, fallidos, estado='COMPLETADO'):
        """Actualiza el estado de una carga masiva"""
        connection = self.get_connection()
        if not connection:
            return False
            
        cursor = connection.cursor()
        
        try:
            cursor.execute('''
                UPDATE cargas_masivas 
                SET registros_exitosos = %s, registros_fallidos = %s, estado = %s
                WHERE id = %s
            ''', (exitosos, fallidos, estado, carga_id))
            
            connection.commit()
            return True
            
        except Error as e:
            print(f"❌ Error al actualizar carga masiva: {e}")
            return False
        finally:
            cursor.close()
            connection.close()
    
    def insert_resolucion(self, numero_resolucion, tipo_resolucion, aprendiz_id, contenido, archivo_path=None):
        """Inserta una nueva resolución"""
        connection = self.get_connection()
        if not connection:
            return None
            
        cursor = connection.cursor()
        
        try:
            cursor.execute('''
                INSERT INTO resoluciones 
                (numero_resolucion, tipo_resolucion, aprendiz_id, contenido, archivo_path)
                VALUES (%s, %s, %s, %s, %s)
            ''', (numero_resolucion, tipo_resolucion, aprendiz_id, contenido, archivo_path))
            
            connection.commit()
            resolucion_id = cursor.lastrowid
            return resolucion_id
            
        except Error as e:
            print(f"❌ Error al insertar resolución: {e}")
            return None
        finally:
            cursor.close()
            connection.close()