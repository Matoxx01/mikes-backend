import os
import mysql.connector
from mysql.connector import Error
from dotenv import load_dotenv
from typing import List, Dict, Any, Tuple, Optional, Union

# Cargar variables de entorno
load_dotenv()

class Database:
    def __init__(self):
        self.connection = None

    def connect(self):
        if not self.connection or not self.connection.is_connected():
            try:
                self.connection = mysql.connector.connect(
                    host=os.getenv('DB_HOST'),
                    port=int(os.getenv('DB_PORT', '3306')),
                    user=os.getenv('DB_USER'),
                    password=os.getenv('DB_PASSWORD'),
                    database=os.getenv('DB_NAME')
                )
                print("🔌 Conectado a MySQL en", os.getenv("DB_HOST"))
            except Error as e:
                print("❌ Error conectando a MySQL:", e)
                raise

    def execute_query(self, query: str, params: tuple = None) -> Tuple[List[Dict], Optional[int]]:
        """Ejecuta una consulta SQL y devuelve los resultados y el último ID insertado"""
        self.connect()
        cursor = self.connection.cursor(dictionary=True)
        try:
            cursor.execute(query, params or ())
            last_id = cursor.lastrowid
            
            # Solo para consultas SELECT
            if query.strip().upper().startswith('SELECT'):
                result = cursor.fetchall()
            else:
                result = []
                
            self.connection.commit()
            return result, last_id
        except Error as e:
            self.connection.rollback()
            print(f"Error executing query: {e}")
            raise e
        finally:
            cursor.close()

    def begin_transaction(self):
        self.connection.start_transaction()

    def commit(self):
        self.connection.commit()

    def rollback(self):
        self.connection.rollback()

# Instancia global de la base de datos
db = Database()

# Comprobar nombre
async def get_user_by_name(name: str) -> Dict:
    sql = 'SELECT idEmployee, name, password, role FROM employee WHERE name = %s LIMIT 1'
    results, _ = db.execute_query(sql, (name,))
    return results[0] if results else None

# Comprobar clave
async def authenticate(name: str, password: str) -> Dict:
    user = await get_user_by_name(name)
    if not user:
        # nombre no existe
        return {"ok": False, "reason": "name"}
    
    if user['password'] != password:
        # clave incorrecta
        return {"ok": False, "reason": "password"}
    
    # éxito
    return {
        "ok": True,
        "user": {
            "id": user['idEmployee'],
            "name": user['name'],
            "role": user['role']
        }
    }

# Obtener todos los clientes
async def get_client() -> List[Dict]:
    query = 'SELECT idClient, name FROM client'
    results, _ = db.execute_query(query)
    return results

# Agregar un cliente
async def add_client(name: str) -> Dict:
    query = 'INSERT INTO client (name) VALUES (%s)'
    _, last_id = db.execute_query(query, (name,))
    return {"insertId": last_id}

# Obtener todos los empleados
async def get_employee() -> List[Dict]:
    q = 'SELECT idEmployee, name, password, role FROM employee'
    results, _ = db.execute_query(q)
    return results

# Eliminar un empleado
async def delete_employee(id: int) -> None:
    q = 'DELETE FROM employee WHERE idEmployee = %s'
    db.execute_query(q, (id,))

# Actualizar un empleado
async def update_employee(id: int, name: str, password: str, role: str) -> None:
    q = 'UPDATE employee SET name = %s, password = %s, role = %s WHERE idEmployee = %s'
    db.execute_query(q, (name, password, role, id))

# Agregar un nuevo empleado
async def add_employee(name: str, password: str, role: str) -> Dict:
    q = 'INSERT INTO employee (name, password, role) VALUES (%s, %s, %s)'
    _, last_id = db.execute_query(q, (name, password, role))
    return {"insertId": last_id}

# Obtener nóminas según cliente
async def get_nominas(client_id: int) -> List[Dict]:
    q = """
    SELECT idNomina, name 
    FROM nomina 
    WHERE client_idClient = %s
    """
    results, _ = db.execute_query(q, (client_id,))
    return results

# Eliminar una nómina con sus usuarios y su cliente si no quedan nóminas del mismo
async def delete_nomina(id_nomina: int, client_id: int) -> None:
    try:
        db.begin_transaction()
        
        # 1) Obtener IDs de usuarios a borrar
        q0 = 'SELECT idUser FROM app_user WHERE nomina_idNomina = %s'
        users, _ = db.execute_query(q0, (id_nomina,))
        user_ids = [row['idUser'] for row in users]
        
        # 2) Borrar productos de esos usuarios (si hay alguno)
        if user_ids:
            q_prod = 'DELETE FROM product WHERE user_idUser IN ({})'.format(','.join(['%s'] * len(user_ids)))
            db.execute_query(q_prod, tuple(user_ids))
        
        # 3) Borrar usuarios de la nómina
        q1 = 'DELETE FROM app_user WHERE nomina_idNomina = %s'
        db.execute_query(q1, (id_nomina,))

        # 4) Borrar la nómina
        q2 = 'DELETE FROM nomina WHERE idNomina = %s'
        db.execute_query(q2, (id_nomina,))

        # 5) Comprobar si quedan nóminas de ese cliente
        q3 = 'SELECT COUNT(*) AS cnt FROM nomina WHERE client_idClient = %s'
        results, _ = db.execute_query(q3, (client_id,))
        remaining = results[0]['cnt']

        if remaining == 0:
            # 6) Borrar cliente
            q4 = 'DELETE FROM client WHERE idClient = %s'
            db.execute_query(q4, (client_id,))
        
        db.commit()
    except Exception as e:
        db.rollback()
        raise e

# Obtener usuarios
async def get_users(nomina_id: int) -> List[Dict]:
    q = """
    SELECT idUser, rut, name, lastName, sex, area, service, center, signature, comment, nomina_idNomina
    FROM app_user
    WHERE nomina_idNomina = %s
    """
    results, _ = db.execute_query(q, (nomina_id,))
    return results

# Agregar un usuario
async def insert_user(rut: str, name: str, last_name: str, sex: str, area: str, 
                     service: str, center: str, nomina_id: int, client_id: int) -> int:
    q = """
    INSERT INTO app_user
    (rut, name, lastName, sex, area, service, center, nomina_idNomina, nomina_idClient)
    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
    """
    _, last_id = db.execute_query(
        q,
        (rut, name, last_name, sex, area, service, center, nomina_id, client_id)
    )
    return last_id

# Obtener productos
async def get_products(user_id: int) -> List[Dict]:
    q = """
    SELECT idProduct, sku, name, color, quantity, size
    FROM product
    WHERE user_idUser = %s
    """
    results, _ = db.execute_query(q, (user_id,))
    return results

# Actualizar comentario y firma
async def update_user_comment_signature(id_user: int, comment: str, signature: Optional[str], performed_by: str) -> None:
    if signature:
        q = """
        UPDATE app_user
        SET 
            comment = %s,
            signature = %s,
            employee = %s
        WHERE idUser = %s
        """
        params = (comment, signature, performed_by, id_user)
    else:
        q = """
        UPDATE app_user
        SET 
            comment = %s,
            employee = %s
        WHERE idUser = %s
        """
        params = (comment, performed_by, id_user)
    
    db.execute_query(q, params)

# Eliminar usuario y sus productos
async def delete_user(id_user: int) -> None:
    try:
        db.begin_transaction()
        
        # 1) Borrar productos asociados
        q_prod = 'DELETE FROM product WHERE user_idUser = %s'
        db.execute_query(q_prod, (id_user,))
        
        # 2) Borrar usuario
        q_user = 'DELETE FROM app_user WHERE idUser = %s'
        db.execute_query(q_user, (id_user,))
        
        db.commit()
    except Exception as e:
        db.rollback()
        raise e

# Exportar a Excel
async def export_excel_query(nomina_id: int) -> List[Dict]:
    query = """
    SELECT 
        u.rut, u.name AS username, u.lastName, u.area, u.signature,
        p.sku, p.name AS productName, p.color, p.quantity, p.size
    FROM app_user u
    LEFT JOIN product p ON u.idUser = p.user_idUser
    WHERE u.nomina_idNomina = %s
    ORDER BY u.rut
    """
    results, _ = db.execute_query(query, (nomina_id,))
    return results

# Insertar nueva nómina
async def insert_nomina(name: str, client_id: int) -> Dict:
    q = 'INSERT INTO nomina (name, client_idClient) VALUES (%s, %s)'
    _, last_id = db.execute_query(q, (name, client_id))
    return {"insertId": last_id}

# Insertar usuario de Excel
async def insert_excel_user(user: Dict) -> Dict:
    q = """
    INSERT INTO app_user
    (rut, name, lastName, sex, area, service, center, nomina_idNomina, nomina_idClient)
    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
    """
    _, last_id = db.execute_query(
        q,
        (
            user['rut'], 
            user['name'], 
            user['lastName'], 
            user['sex'], 
            user['area'], 
            user['service'], 
            user['center'], 
            user['nomina_idNomina'], 
            user['nomina_idClient']
        )
    )
    return {"insertId": last_id}

# Insertar producto
async def insert_product(product: Dict) -> None:
    q = """
    INSERT INTO product
    (name, color, quantity, size, sku, user_idUser, user_nomina_idNomina, user_nomina_idClient)
    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
    """
    db.execute_query(
        q,
        (
            product['name'],
            product['color'],
            product['quantity'],
            product['size'],
            product['sku'],
            product['user_idUser'],
            product['user_nomina_idNomina'],
            product['user_nomina_idClient']
        )
    )

# Actualizar cantidad de producto
async def update_product_quantity(id_product: int, quantity: int) -> None:
    q = 'UPDATE product SET quantity = %s WHERE idProduct = %s'
    db.execute_query(q, (quantity, id_product))

# Buscar todos los usuarios por nombre, apellido o rut
async def search_all_users(query: str) -> List[Dict]:
    like = f"%{query}%"
    sql = """
    SELECT 
        idUser, rut, name, lastName, nomina_idNomina, nomina_idClient
    FROM app_user
    WHERE rut LIKE %s OR name LIKE %s OR lastName LIKE %s
    LIMIT 3
    """
    results, _ = db.execute_query(sql, (like, like, like))
    return results

# Eliminar cliente y todas sus dependencias
async def delete_client(client_id: int) -> None:
    try:
        db.begin_transaction()
        
        q_prod = 'DELETE FROM product WHERE user_nomina_idClient = %s'
        db.execute_query(q_prod, (client_id,))
        
        q_user = 'DELETE FROM app_user WHERE nomina_idClient = %s'
        db.execute_query(q_user, (client_id,))
        
        q_nom = 'DELETE FROM nomina WHERE client_idClient = %s'
        db.execute_query(q_nom, (client_id,))
        
        q_client = 'DELETE FROM client WHERE idClient = %s'
        db.execute_query(q_client, (client_id,))
        
        db.commit()
    except Exception as e:
        db.rollback()
        raise e

# Actualizar nombre de cliente
async def update_client(id_client: int, name: str) -> None:
    q = 'UPDATE client SET name = %s WHERE idClient = %s'
    db.execute_query(q, (name, id_client))

# Cambiar nombre de nómina
async def changeNominaName(id_nomina: int, new_name: str) -> None:
    """
    Actualiza el campo name de la nómina especificada.
    """
    q = 'UPDATE nomina SET name = %s WHERE idNomina = %s'
    db.execute_query(q, (new_name, id_nomina))

# Eliminar un producto
async def delete_product(id_product: int) -> None:
    q = 'DELETE FROM product WHERE idProduct = %s'
    db.execute_query(q, (id_product,))

# Actualizar talla de un producto
async def update_product_size(id_product: int, size: str) -> None:
    q = 'UPDATE product SET size = %s WHERE idProduct = %s'
    db.execute_query(q, (size, id_product))

# Añadir un producto
async def insert_product_return_id(product: Dict[str, Any]) -> int:
    """
    Inserta un producto y devuelve el idProduct generado.
    Espera un dict con las mismas keys que ProductData.
    """
    q = """
    INSERT INTO product
      (sku, name, color, quantity, size,
       user_idUser, user_nomina_idNomina, user_nomina_idClient)
    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
    """
    params = (
        product['sku'],
        product['name'],
        product['color'],
        product['quantity'],
        product['size'],
        product['user_idUser'],
        product['user_nomina_idNomina'],
        product['user_nomina_idClient']
    )
    # Ejecuta y captura el lastrowid
    _, last_id = db.execute_query(q, params)
    return last_id
