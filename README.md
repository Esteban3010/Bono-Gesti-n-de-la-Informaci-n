# Sistema de Consulta Veterinaria

Aplicación web desarrollada con **Python, Flask y Oracle Database** para consultar la ficha de una mascota mediante su identificador. Presenta la información en una interfaz organizada, con una ficha principal y secciones desplegables para los datos adicionales.

## Tecnologías utilizadas

- **Python + Flask:** servidor web y procesamiento de consultas.
- **Oracle Database:** almacenamiento de la información de la veterinaria.
- **python-oracledb:** conexión de Python con Oracle.
- **HTML + CSS:** estructura y diseño de la interfaz.
- **Jinja2:** generación del HTML con los resultados obtenidos.
- **OneGate + SSH:** acceso al servidor Oracle de la universidad.

## Requisitos previos

Antes de comenzar, necesitas:

1. **Python 3** y `pip` instalados.
2. Acceso a **OneGate / TunnelClient** y al servidor **SVRING1** de la universidad.
3. Un usuario de Oracle con permisos de lectura sobre las tablas del proyecto.
4. Acceso a la base de datos veterinaria en el servicio **`FREEPDB1`**.
5. Un cliente SSH disponible en el computador (por ejemplo, OpenSSH en Windows).

> **Importante:** la base de datos está alojada en un servidor institucional. Descargar el repositorio no otorga acceso a Oracle: para realizar búsquedas reales necesitas las credenciales y el acceso remoto autorizados.

## Estructura del proyecto

```text
sistema-veterinaria/
├── app.py
├── README.md
└── templates/
    └── index.html
```

El archivo `index.html` debe permanecer dentro de la carpeta **`templates/`**, porque Flask lo carga mediante `render_template()`.

## Instalación y ejecución paso a paso

Las instrucciones principales están pensadas para **Windows con PowerShell**.

### Paso 1. Descargar el proyecto

Clona el repositorio y entra a su carpeta:

```powershell
git clone <URL_DEL_REPOSITORIO>
cd <CARPETA_DEL_REPOSITORIO>
```

También puedes descargarlo desde GitHub mediante **Code → Download ZIP** y descomprimirlo.

### Paso 2. Crear un entorno virtual de Python (Opcional)

Desde la carpeta donde se encuentra `app.py`, ejecuta:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
```

El entorno virtual permite instalar las dependencias sin afectar otras aplicaciones de Python.

> Si PowerShell bloquea la activación, puedes utilizar directamente `.\.venv\Scripts\python.exe` en lugar de `python` en los siguientes comandos, sin activar el entorno.

### Paso 3. Instalar las dependencias

Con el entorno virtual activado, ejecuta:

```powershell
python -m pip install flask oracledb
```

Estas son las dos dependencias externas que utiliza `app.py`.

### Paso 4. Establecer el acceso remoto con OneGate

1. Inicia sesión en **OneGate** con tu cuenta institucional.
2. Selecciona el acceso al servidor **SVRING1**.
3. Inicia **TunnelClient** y verifica que la conexión esté activa.
4. Mantén esa conexión abierta mientras utilices la aplicación.

### Paso 5. Crear el túnel SSH hacia Oracle

Abre **otra ventana de PowerShell** y ejecuta:

```powershell
ssh -N -L 1521:localhost:1521 linux@127.0.0.1 -p 2222
```

Introduce las credenciales SSH autorizadas si el sistema las solicita.

Este comando reenvía el puerto local **1521** al puerto **1521** del servidor remoto, a través de SSH. De esta manera, la aplicación puede conectarse a Oracle utilizando:

```text
127.0.0.1:1521/FREEPDB1
```

**Deja abierta esta ventana de PowerShell:** cerrar el túnel interrumpirá las consultas a Oracle. Es normal que el comando permanezca ejecutándose sin mostrar mensajes.

> El comando corresponde a la configuración de acceso remoto utilizada en este proyecto. Si la universidad cambia el acceso o el puerto de TunnelClient, deberás actualizarlo.

### Paso 6. Configurar las credenciales de Oracle

Regresa a la ventana de PowerShell donde activaste el entorno virtual y define las variables de entorno:

```powershell
$env:ORACLE_USER="TU_USUARIO_ORACLE"
$env:ORACLE_PASSWORD="TU_CONTRASEÑA_ORACLE"
$env:ORACLE_DSN="127.0.0.1:1521/FREEPDB1"
```

Reemplaza los valores de ejemplo por las credenciales que tengas autorizadas.

Estas variables son leídas por la función `conectar()` de `app.py`. Debes establecerlas **en la misma terminal donde iniciarás Flask**, porque las variables definidas así solo están disponibles en esa sesión.

**Seguridad antes de publicar en GitHub:** la versión inicial de `app.py` conserva credenciales de respaldo dentro de `os.getenv(...)`. Elimina esos valores del código y exige las variables de entorno, por ejemplo:

```python
def conectar():
    return oracledb.connect(
        user=os.environ["ORACLE_USER"],
        password=os.environ["ORACLE_PASSWORD"],
        dsn=os.environ["ORACLE_DSN"],
    )
```

Nunca subas contraseñas, archivos `.env` con credenciales ni claves SSH al repositorio. Si una contraseña real ya fue publicada, cámbiala.

### Paso 7. Iniciar Flask

Desde la carpeta raíz del proyecto, ejecuta:

```powershell
python app.py
```

Si el servidor inicia correctamente, Flask mostrará una dirección similar a:

```text
Running on http://127.0.0.1:5000
```

Mantén esta terminal abierta mientras utilizas la página.

### Paso 8. Abrir la aplicación y consultar una mascota

En tu navegador, entra a:

**http://127.0.0.1:5000**

Luego:

1. Introduce un **ID de mascota** que exista en Oracle (por ejemplo, `1` si está cargado en tu base de datos).
2. Presiona **Buscar mascota**.
3. Consulta la ficha principal.
4. Despliega los recuadros inferiores para revisar la información adicional.

La aplicación permite visualizar:

- **Ficha principal:** nombre, especie, raza, sexo, edad, fecha de nacimiento y esterilización.
- **Salud y antecedentes:** alergias y condiciones médicas.
- **Propietarios y contactos:** información del responsable y contacto auxiliar.
- **Atenciones y citas:** servicios, fechas, profesional asignado y detalles clínicos disponibles.
- **Vacunación:** vacunas, dosis y fechas registradas.
- **Exámenes de laboratorio:** órdenes y tipos de exámenes solicitados.

## ¿Cómo funciona el proyecto?

El flujo de una búsqueda es el siguiente:

```text
Usuario (navegador)
        │
        │ 1. GET /?id=1
        ▼
Flask (app.py)
        │
        │ 2. Valida el ID y prepara las consultas SQL
        ▼
python-oracledb
        │
        │ 3. Conecta a Oracle por el túnel SSH
        ▼
Oracle (SVRING1)
        │
        │ 4. Ejecuta las consultas y devuelve registros
        ▼
Flask + Jinja2
        │
        │ 5. Procesa los datos y genera index.html
        ▼
Navegador
        └── 6. Muestra la ficha y los recuadros desplegables
```

El formulario HTML envía el identificador de la mascota mediante el método **GET**. Flask lo recibe con `request.args`, valida el valor y ejecuta consultas SQL parametrizadas sobre Oracle.

Cuando encuentra la mascota, recupera sus datos principales y la información relacionada (propietarios, atenciones, vacunas y exámenes). Después, **Jinja2** inserta esos resultados en la plantilla `index.html` y Flask devuelve la página HTML al navegador.

Los recuadros se expanden mediante las etiquetas HTML `<details>` y `<summary>`; **abrirlos o cerrarlos no realiza nuevas consultas**. En la versión actual, cada nueva búsqueda carga una página con los resultados correspondientes.

## Solución de problemas frecuentes

| Problema | Qué revisar |
|---|---|
| `ModuleNotFoundError: No module named 'flask'` o `'oracledb'` | Activa el entorno virtual e instala las dependencias del paso 3. |
| Error al conectar con Oracle | Verifica OneGate, TunnelClient, la ventana del túnel SSH y las variables de entorno. |
| `ORA-00942` (tabla o vista no existe) | Comprueba que el usuario Oracle tenga acceso a las tablas del modelo veterinario. |
| `TemplateNotFound: index.html` | Confirma que el archivo esté en `templates/index.html`. |
| No se encuentra la mascota | Utiliza un ID que exista en la tabla `MASCOTA`. |
| El puerto 5000 está ocupado | Cierra el proceso que lo utiliza o inicia Flask en otro puerto con `python -m flask --app app run --port 5001`. |

## Notas

- La aplicación **consulta información**; no incluye formularios para crear, modificar o eliminar registros.
- Las consultas están diseñadas para el modelo relacional Oracle del proyecto veterinario. Si cambian los nombres de las tablas o columnas, será necesario actualizar las sentencias SQL de `app.py`.
- El servidor integrado de Flask se utiliza aquí para **desarrollo local**, no como servidor de producción.
- Para compartir el repositorio, agrega al archivo `.gitignore` al menos `.venv/`, `__pycache__/`, `.env` y `*.pyc`.

---

**Proyecto académico de gestión de información — Sistema de Consulta Veterinaria.**
