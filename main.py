from fastapi import FastAPI, HTTPException, Request, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Optional, List, Dict, Any, Union
import os
import uvicorn

app = FastAPI(
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
    get_report_counts
)

# Configuración de CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Permitir todos los orígenes
    allow_credentials=True,
    allow_methods=["*"],  # Permitir todos los métodos
    allow_headers=["*"],  # Permitir todos los headers
)

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

# Guardar nueva talla
class SizeData(BaseModel):
    size: str

# Ruta raíz para verificar que la API está funcionando
@app.get("/", tags=["Test"])
async def root():
    return {"message": "API funcionando correctamente"}

# Login
@app.post("/login", tags=["Empleados"])
async def login(data: LoginData):
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
async def client_list():
    try:
        results = await get_client()
        return results
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al obtener clientes: {str(e)}")

# Agregar cliente
@app.post("/client", tags=["Clientes"])
async def client_add(data: ClientData):
    if not data.name:
        raise HTTPException(status_code=400, detail="Nombre requerido")
    
    try:
        result = await add_client(data.name)
        return {"success": True, "id": result["insertId"]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al agregar cliente: {str(e)}")

# Listar empleados
@app.get("/employees", tags=["Empleados"])
async def employee_list():
    try:
        results = await get_employee()
        return results
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al obtener empleados: {str(e)}")

# Eliminar empleado
@app.delete("/employee/{id}", tags=["Empleados"])
async def employee_delete(id: int):
    try:
        await delete_employee(id)
        return {"success": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al eliminar empleado: {str(e)}")

# Actualizar empleado
@app.put("/employee/{id}", tags=["Empleados"])
async def employee_update(id: int, data: EmployeeData):
    try:
        await update_employee(id, data.name, data.password, data.role)
        return {"success": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al actualizar empleado: {str(e)}")

# Crear empleado
@app.post("/employee", tags=["Empleados"])
async def employee_create(data: EmployeeData):
    if not data.name or not data.password or not data.role:
        raise HTTPException(status_code=400, detail="Datos incompletos")
    
    try:
        result = await add_employee(data.name, data.password, data.role)
        return {"success": True, "id": result["insertId"]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al agregar empleado: {str(e)}")

# Obtener nóminas de un cliente dado
@app.get("/nomina", tags=["Nominas"])
async def nomina_list(clientId: int):
    if not clientId:
        raise HTTPException(status_code=400, detail="Falta clientId en la query")
    
    try:
        results = await get_nominas(clientId)
        return results
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al obtener nóminas: {str(e)}")

# Eliminar nómina + usuarios asociados + posible cliente
@app.delete("/nomina/{id}", tags=["Nominas"])
async def nomina_delete(id: int, clientId: int):
    try:
        await delete_nomina(id, clientId)
        return {"success": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al eliminar nómina: {str(e)}")

# Obtener usuarios
@app.get("/users", tags=["Usuarios"])
async def user_list(nominaId: int):
    if not nominaId:
        raise HTTPException(status_code=400, detail="Falta nominaId en la query")
    
    try:
        results = await get_users(nominaId)
        return results
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al obtener usuarios: {str(e)}")

# Agregar usuario
@app.post("/user", tags=["Usuarios"])
async def user_add(data: UserData):
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
async def product_list(userId: int):
    if not userId:
        raise HTTPException(status_code=400, detail="Falta userId en la query")
    
    try:
        results = await get_products(userId)
        return results
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error interno al obtener productos: {str(e)}")

# Actualizar comentario y firma de un usuario
@app.put("/user/{id}/comment", tags=["Usuarios"])
async def user_update_comment(id: int, data: CommentData):
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
async def user_delete(id: int):
    try:
        await delete_user(id)
        return {"success": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error interno al eliminar usuario: {str(e)}")

# Exportar a Excel
@app.get("/exportExcel", tags=["Excel"])
async def export_excel(nominaId: int):
    if not nominaId:
        raise HTTPException(status_code=400, detail="Falta el parámetro nominaId")
    
    try:
        results = await export_excel_query(nominaId)
        return results
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al exportar datos: {str(e)}")

# Agregar nómina
@app.post("/nomina", tags=["Excel"])
async def nomina_add(data: NominaData):
    try:
        result = await insert_nomina(data.name, data.client_idClient)
        return {"idNomina": result["insertId"]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error interno al crear nómina: {str(e)}")

# Agregar usuario desde Excel
@app.post("/app_user", tags=["Excel"])
async def user_add_excel(data: ExcelUserData):
    try:
        result = await insert_excel_user(data.dict())
        return {"idUser": result["insertId"]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error interno al crear usuario: {str(e)}")

# Agregar producto
@app.post("/product", tags=["Excel"])
async def product_add(data: ProductData):
    try:
        await insert_product(data.dict())
        return {"success": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error interno al crear producto: {str(e)}")

# Actualizar cantidad de producto
@app.put("/product/{id}", tags=["Productos"])
async def product_update_quantity(id: int, data: ProductQuantityData):
    if data.quantity is None:
        raise HTTPException(status_code=400, detail="Falta quantity")
    
    try:
        await update_product_quantity(id, data.quantity)
        return {"success": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error interno: {str(e)}")

# Buscar usuarios
@app.get("/users/search", tags=["Usuarios"])
async def users_search(q: Optional[str] = None):
    if not q:
        return []
    
    try:
        users = await search_all_users(q)
        return users
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error interno al buscar usuarios: {str(e)}")

# Eliminar cliente y todas sus dependencias
@app.delete("/client/{idClient}", tags=["Clientes"])
async def client_delete(idClient: int):
    try:
        await delete_client(idClient)
        return {"success": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al eliminar cliente: {str(e)}")

# Actualizar nombre de cliente
@app.put("/client/{idClient}", tags=["Clientes"])
async def client_update(idClient: int, data: ClientData):
    if not data.name:
        raise HTTPException(status_code=400, detail="Nombre requerido")
    
    try:
        await update_client(idClient, data.name)
        return {"success": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error interno al actualizar cliente: {str(e)}")

# Cambiar nombre Nomina
@app.put("/nomina/changeName", tags=["Nominas"])
async def nomina_change_name(data: NominaChangeData):
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
async def product_delete(id: int):
    try:
        await delete_product(id)
        return {"success": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Guardar talla de producto
@app.put("/product/saveSize/{id}", tags=["Productos"])
async def product_save_size(id: int, data: SizeData):
    if not data.size:
        raise HTTPException(status_code=400, detail="Falta size")
    try:
        await update_product_size(id, data.size)
        return {"success": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Agregar producto
@app.post("/product/add", tags=["Productos"])
async def product_add(data: ProductData):
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

@app.get("/report", tags=["Reporte"])
async def report(nominaId: int):
    if not nominaId:
        raise HTTPException(status_code=400, detail="Falta nominaId")
    try:
        result = await get_report_counts(nominaId)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al obtener reporte: {str(e)}")

if __name__ == "__main__":
    port = int(os.getenv("PORT", 3000))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=True)