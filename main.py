from fastapi import FastAPI, HTTPException, Request, status, APIRouter, Depends, Security
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Optional, List, Dict, Any, Union
from fastapi.security.api_key import APIKeyHeader
import os
import uvicorn
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(
    docs_url=None,
    redoc_url=None,
    openapi_url=None,
    title="Mike's APIs",
    description="APIs en produccion de Mike's",
    version="1.0.0",
)

# Importamos todas las funciones de db.py
from db import (
    authenticate, add_client, get_client, get_employee, delete_employee,
    update_employee, add_employee, get_nominas, delete_nomina, get_users,
    insert_user, get_products, update_user_comment_signature, delete_user,
    export_excel_query, insert_nomina, insert_excel_user, insert_product,
    update_product_quantity, search_all_users, delete_client, update_client,
    changeNominaName, delete_product, update_product_size, insert_product_return_id,
    get_report_counts, insert_bulk_users_products, get_users_with_products, get_all_products,
    export_optimized_query
)

# Configuración de CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Permitir todos los orígenes
    allow_credentials=True,
    allow_methods=["*"],  # Permitir todos los métodos
    allow_headers=["*"],  # Permitir todos los headers
)

# --- Carga de API Keys desde variable de entorno ---
API_KEY = os.getenv("API_KEY")

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)

async def require_api_key(api_key: str = Security(api_key_header)):
    if not API_KEY:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="API no configurada")
    if not api_key or api_key not in API_KEY:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No autorizado")
    return api_key

@app.get("/hello")
async def hello(api_key: str = Depends(require_api_key)):
    return {"message": "Hola desde la API protegida"}

# Rutas estáticas para cuando sea necesario servir archivos estáticos
if os.path.exists("../public"):
    app.mount("/static", StaticFiles(directory="../public"), name="static")
elif os.path.exists("./public"):
    app.mount("/static", StaticFiles(directory="./public"), name="static")

# Modelos de datos para validación

class LoginData(BaseModel):
    name: str
    password: str

class ClientData(BaseModel):
    name: str

class EmployeeData(BaseModel):
    name: str
    password: str
    role: str

class CommentData(BaseModel):
    comment: Optional[str] = None
    signature: Optional[str] = None
    performedBy: str
    signatureDate: str

class NominaData(BaseModel):
    name: str
    client_idClient: int

class ProductQuantityData(BaseModel):
    quantity: int

class UserData(BaseModel):
    rut: str
    name: str
    lastName: str
    sex: str
    area: str
    service: str
    center: str
    signature: Optional[str] = None
    comment: Optional[str] = None
    nominaId: int
    clientId: int

class ProductData(BaseModel):
    name: str
    color: str
    quantity: int
    size: str
    sku: str
    user_idUser: int
    user_nomina_idNomina: int
    user_nomina_idClient: int

class ExcelUserData(BaseModel):
    rut: str
    name: str
    lastName: str
    sex: str
    area: str
    service: str
    center: str
    nomina_idNomina: int
    nomina_idClient: int

class NominaChangeData(BaseModel):
    idNomina: int
    name: str

class BulkProduct(BaseModel):
    name: str
    color: Optional[str] = ""
    quantity: Optional[int] = 0
    size: Optional[str] = ""
    sku: Optional[str] = ""

class BulkUser(BaseModel):
    rut: str
    name: str
    lastName: str
    sex: Optional[str] = ""
    area: Optional[str] = ""
    service: Optional[str] = ""
    center: Optional[str] = ""
    products: Optional[List[BulkProduct]] = []

class BulkImportData(BaseModel):
    nomina_idNomina: int
    nomina_idClient: int
    users: List[BulkUser]

# Guardar nueva talla
class SizeData(BaseModel):
    size: str

# Login
@app.post("/login", tags=["Empleados"])
async def login(data: LoginData, api_key: str = Depends(require_api_key)):
    if not data.name or not data.password:
        raise HTTPException(status_code=400, detail="Falta nombre o clave")
    
    result = await authenticate(data.name, data.password)
    
    if not result["ok"]:
        msg = "Nombre incorrecto" if result["reason"] == "name" else "Clave incorrecta"
        raise HTTPException(status_code=401, detail=msg)
    
    # autenticación exitosa
    return {
        "role": result["user"]["role"],
        "name": result["user"]["name"]
    }

# Obtener el cliente
@app.get("/client", tags=["Clientes"])
async def client_list(api_key: str = Depends(require_api_key)):
    try:
        results = await get_client()
        return results
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al obtener clientes: {str(e)}")

# Agregar cliente
@app.post("/client", tags=["Clientes"])
async def client_add(data: ClientData, api_key: str = Depends(require_api_key)):
    if not data.name:
        raise HTTPException(status_code=400, detail="Nombre requerido")
    
    try:
        result = await add_client(data.name)
        return {"success": True, "id": result["insertId"]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al agregar cliente: {str(e)}")

# Listar empleados
@app.get("/employees", tags=["Empleados"])
async def employee_list(api_key: str = Depends(require_api_key)):
    try:
        results = await get_employee()
        return results
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al obtener empleados: {str(e)}")

# Eliminar empleado
@app.delete("/employee/{id}", tags=["Empleados"])
async def employee_delete(id: int, api_key: str = Depends(require_api_key)):
    try:
        await delete_employee(id)
        return {"success": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al eliminar empleado: {str(e)}")

# Actualizar empleado
@app.put("/employee/{id}", tags=["Empleados"])
async def employee_update(id: int, data: EmployeeData, api_key: str = Depends(require_api_key)):
    try:
        await update_employee(id, data.name, data.password, data.role)
        return {"success": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al actualizar empleado: {str(e)}")

# Crear empleado
@app.post("/employee", tags=["Empleados"])
async def employee_create(data: EmployeeData, api_key: str = Depends(require_api_key)):
    if not data.name or not data.password or not data.role:
        raise HTTPException(status_code=400, detail="Datos incompletos")
    
    try:
        result = await add_employee(data.name, data.password, data.role)
        return {"success": True, "id": result["insertId"]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al agregar empleado: {str(e)}")

# Obtener nóminas de un cliente dado
@app.get("/nomina", tags=["Nominas"])
async def nomina_list(clientId: int, api_key: str = Depends(require_api_key)):
    if not clientId:
        raise HTTPException(status_code=400, detail="Falta clientId en la query")
    
    try:
        results = await get_nominas(clientId)
        return results
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al obtener nóminas: {str(e)}")

# Eliminar nómina + usuarios asociados + productos asociados
@app.delete("/nomina/{id}", tags=["Nominas"])
async def nomina_delete(id: int, clientId: int, api_key: str = Depends(require_api_key)):
    try:
        await delete_nomina(id, clientId)
        return {"success": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al eliminar nómina: {str(e)}")

# Obtener usuarios
@app.get("/users", tags=["Usuarios"])
async def user_list(nominaId: int, api_key: str = Depends(require_api_key)):
    if not nominaId:
        raise HTTPException(status_code=400, detail="Falta nominaId en la query")
    
    try:
        results = await get_users(nominaId)
        return results
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al obtener usuarios: {str(e)}")

# Agregar usuario
@app.post("/user", tags=["Usuarios"])
async def user_add(data: UserData, api_key: str = Depends(require_api_key)):
    required_fields = ["rut", "name", "lastName", "sex", "area", "service", "center", "nominaId", "clientId"]
    for field in required_fields:
        if not hasattr(data, field) or not getattr(data, field):
            raise HTTPException(status_code=400, detail=f"Faltan datos para crear usuario: {field}")
    
    try:
        insert_id = await insert_user(
            data.rut, data.name, data.lastName, data.sex, data.area, 
            data.service, data.center, data.nominaId, data.clientId
        )
        return {"success": True, "idUser": insert_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error interno al crear usuario: {str(e)}")

# Obtener productos
@app.get("/products", tags=["Productos"])
async def product_list(userId: int, api_key: str = Depends(require_api_key)):
    if not userId:
        raise HTTPException(status_code=400, detail="Falta userId en la query")
    
    try:
        results = await get_products(userId)
        return results
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error interno al obtener productos: {str(e)}")
    
# Obtener todos los productos
@app.get("/allproducts", tags=["Productos"])
async def product_list(api_key: str = Depends(require_api_key)):    
    try:
        results = await get_all_products()
        return results
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error interno al obtener productos: {str(e)}")

# Actualizar comentario y firma de un usuario
@app.put("/user/{id}/comment", tags=["Usuarios"])
async def user_update_comment(id: int, data: CommentData, api_key: str = Depends(require_api_key)):
    # Validación mejorada
    if data.comment is None or not data.performedBy:
        raise HTTPException(status_code=400, detail="Datos incompletos")
    
    try:
        await update_user_comment_signature(id, data.comment, data.signature, data.performedBy, data.signatureDate)
        return {"success": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al actualizar: {str(e)}")

# Eliminar usuario
@app.delete("/user/{id}", tags=["Usuarios"])
async def user_delete(id: int, api_key: str = Depends(require_api_key)):
    try:
        await delete_user(id)
        return {"success": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error interno al eliminar usuario: {str(e)}")

# Exportar a Excel
@app.get("/exportExcel", tags=["Excel"])
async def export_excel(nominaId: int, api_key: str = Depends(require_api_key)):
    if not nominaId:
        raise HTTPException(status_code=400, detail="Falta el parámetro nominaId")
    
    try:
        results = await export_excel_query(nominaId)
        return results
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al exportar datos: {str(e)}")

# Exportar datos optimizados
@app.get("/exportOptimized", tags=["Excel"])
async def export_optimized(nominaId: int, signedOnly: bool = False, api_key: str = Depends(require_api_key)):
    if not nominaId:
        raise HTTPException(status_code=400, detail="Falta el parámetro nominaId")
    
    try:
        results = await export_optimized_query(nominaId, signedOnly)
        return results
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al exportar datos: {str(e)}")

# Agregar nómina
@app.post("/nomina", tags=["Excel"])
async def nomina_add(data: NominaData, api_key: str = Depends(require_api_key)):
    try:
        result = await insert_nomina(data.name, data.client_idClient)
        return {"idNomina": result["insertId"]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error interno al crear nómina: {str(e)}")

# Agregar usuario desde Excel
@app.post("/app_user", tags=["Excel"])
async def user_add_excel(data: ExcelUserData, api_key: str = Depends(require_api_key)):
    try:
        result = await insert_excel_user(data.dict())
        return {"idUser": result["insertId"]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error interno al crear usuario: {str(e)}")

# Agregar producto
@app.post("/product", tags=["Excel"])
async def product_add(data: ProductData, api_key: str = Depends(require_api_key)):
    try:
        await insert_product(data.dict())
        return {"success": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error interno al crear producto: {str(e)}")

# Actualizar cantidad de producto
@app.put("/product/{id}", tags=["Productos"])
async def product_update_quantity(id: int, data: ProductQuantityData, api_key: str = Depends(require_api_key)):
    if data.quantity is None:
        raise HTTPException(status_code=400, detail="Falta quantity")
    
    try:
        await update_product_quantity(id, data.quantity)
        return {"success": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error interno: {str(e)}")

# Buscar usuarios
@app.get("/users/search", tags=["Usuarios"])
async def users_search(q: Optional[str] = None, api_key: str = Depends(require_api_key)):
    if not q:
        return []
    
    try:
        users = await search_all_users(q)
        return users
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error interno al buscar usuarios: {str(e)}")

# Eliminar cliente y todas sus dependencias
@app.delete("/client/{idClient}", tags=["Clientes"])
async def client_delete(idClient: int, api_key: str = Depends(require_api_key)):
    try:
        await delete_client(idClient)
        return {"success": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al eliminar cliente: {str(e)}")

# Actualizar nombre de cliente
@app.put("/client/{idClient}", tags=["Clientes"])
async def client_update(idClient: int, data: ClientData, api_key: str = Depends(require_api_key)):
    if not data.name:
        raise HTTPException(status_code=400, detail="Nombre requerido")
    
    try:
        await update_client(idClient, data.name)
        return {"success": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error interno al actualizar cliente: {str(e)}")

# Cambiar nombre Nomina
@app.put("/nomina/changeName", tags=["Nominas"])
async def nomina_change_name(data: NominaChangeData, api_key: str = Depends(require_api_key)):
    """
    Cambia el nombre de una nómina.
    """
    if not data.name.strip():
        raise HTTPException(status_code=400, detail="Nombre vacío")
    try:
        await changeNominaName(data.idNomina, data.name)
        return {"success": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al cambiar nombre: {str(e)}")
    
# Eliminar producto
@app.delete("/product/del/{id}", tags=["Productos"])
async def product_delete(id: int, api_key: str = Depends(require_api_key)):
    try:
        await delete_product(id)
        return {"success": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Guardar talla de producto
@app.put("/product/saveSize/{id}", tags=["Productos"])
async def product_save_size(id: int, data: SizeData, api_key: str = Depends(require_api_key)):
    if not data.size:
        raise HTTPException(status_code=400, detail="Falta size")
    try:
        await update_product_size(id, data.size)
        return {"success": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Agregar producto
@app.post("/product/add", tags=["Productos"])
async def product_add(data: ProductData, api_key: str = Depends(require_api_key)):
    """
    Añade un producto vinculado a un usuario, nómina y cliente.
    Devuelve el nuevo idProduct.
    """
    # Validación mínima
    required = ["name", "user_idUser", "user_nomina_idNomina", "user_nomina_idClient"]
    for field in required:
        if getattr(data, field) is None:
            raise HTTPException(status_code=400, detail=f"Falta '{field}'")

    try:
        new_id = await insert_product_return_id(data.dict())
        return {"success": True, "idProduct": new_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al insertar producto: {e}")

# Obtener reporte de conteos
@app.get("/report", tags=["Reporte"])
async def report(nominaId: int, api_key: str = Depends(require_api_key)):
    if not nominaId:
        raise HTTPException(status_code=400, detail="Falta nominaId")
    try:
        result = await get_report_counts(nominaId)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al obtener reporte: {str(e)}")

# Importación masiva de usuarios y productos
@app.post("/import_bulk", tags=["Excel"])
async def import_bulk(data: BulkImportData, api_key: str = Depends(require_api_key)):
    try:
        result = await insert_bulk_users_products(data.dict())
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error interno al importar: {str(e)}")

# Obtener usuarios con productos
@app.get("/users_with_products", tags=["Usuarios"])
async def users_with_products(nominaId: int, api_key: str = Depends(require_api_key)):
    """
    Devuelve todos los usuarios de una nómina con sus productos incluidos (en 'products').
    Uso: /users_with_products?nominaId=123
    """
    if not nominaId:
        raise HTTPException(status_code=400, detail="Falta nominaId en la query")
    try:
        results = await get_users_with_products(nominaId)
        return results
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error interno al obtener usuarios con productos: {str(e)}")

# Manejo de errores 404
@app.exception_handler(404)
async def not_found_handler(request, exc):
    raise HTTPException(status_code=404, detail="Página no encontrada")

# Ejecutar la aplicación
if __name__ == "__main__":
    port = int(os.getenv("PORT", 3000))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=True)