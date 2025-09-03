# verify_database.py - Verificar estado de la base de datos
import sys
from pathlib import Path
import sqlite3


def verify_database():
    """Verifica el estado completo de la base de datos"""

    # Determinar el directorio correcto
    current_dir = Path.cwd()
    if current_dir.name == 'app':
        # Si estamos en app/, el data/ está en el padre
        project_root = current_dir.parent
    elif (current_dir / 'app').exists():
        # Si estamos en la raíz del proyecto
        project_root = current_dir
    else:
        project_root = current_dir

    db_path = project_root / "data" / "finance_app.db"

    print("🔍 VERIFICACIÓN DE BASE DE DATOS")
    print("=" * 50)
    print(f"📁 Directorio actual: {current_dir}")
    print(f"📁 Raíz proyecto: {project_root}")
    print(f"📁 Archivo BD: {db_path}")
    print(f"📁 Existe: {db_path.exists()}")

    if not db_path.exists():
        print("❌ La base de datos no existe. Ejecuta la app primero para crearla.")
        return

    # 2. Verificar tamaño
    size_mb = db_path.stat().st_size / (1024 * 1024)
    print(f"📏 Tamaño: {size_mb:.2f} MB")

    # 3. Conectar y verificar tablas
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        print("\n📋 TABLAS EN LA BASE DE DATOS:")
        print("-" * 30)

        # Listar todas las tablas
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = cursor.fetchall()

        for (table_name,) in tables:
            print(f"✅ {table_name}")

            # Contar registros en cada tabla
            cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
            count = cursor.fetchone()[0]
            print(f"   📊 Registros: {count}")

            # Mostrar estructura de tabla
            cursor.execute(f"PRAGMA table_info({table_name})")
            columns = cursor.fetchall()
            print(f"   📝 Columnas: {[col[1] for col in columns]}")
            print()

        # 4. Verificar datos específicos
        print("🏷️ CATEGORÍAS:")
        print("-" * 20)
        cursor.execute("SELECT name, description, created_at FROM categories WHERE is_active = 1")
        categories = cursor.fetchall()

        if categories:
            for name, desc, created in categories:
                print(f"  • {name}: {desc or 'Sin descripción'} ({created})")
        else:
            print("  ⚠️ No hay categorías")

        print(f"\n👥 CONTACTOS:")
        print("-" * 20)
        cursor.execute("SELECT rut, name, alias FROM contacts WHERE is_active = 1")
        contacts = cursor.fetchall()

        if contacts:
            for rut, name, alias in contacts[:5]:  # Mostrar primeros 5
                display_name = f"{name} ({alias})" if alias else name
                print(f"  • {rut} → {display_name}")
            if len(contacts) > 5:
                print(f"  ... y {len(contacts) - 5} más")
        else:
            print("  ⚠️ No hay contactos")

        print(f"\n💾 TRANSACCIONES ETIQUETADAS:")
        print("-" * 30)
        cursor.execute("SELECT COUNT(*) FROM labeled_transactions")
        total_transactions = cursor.fetchone()[0]
        print(f"📊 Total: {total_transactions}")

        if total_transactions > 0:
            # Mostrar últimas 3 transacciones
            cursor.execute("""
                SELECT date, description, amount, category, created_at 
                FROM labeled_transactions 
                ORDER BY created_at DESC 
                LIMIT 3
            """)
            recent = cursor.fetchall()

            print("📝 Últimas transacciones:")
            for date, desc, amount, cat, created in recent:
                print(f"  • {date} | {desc[:40]}... | ${amount:,.0f} | {cat} | {created}")

            # Distribución por categoría
            cursor.execute("""
                SELECT category, COUNT(*) as count, SUM(amount) as total_amount
                FROM labeled_transactions 
                GROUP BY category 
                ORDER BY count DESC
            """)
            category_stats = cursor.fetchall()

            print("\n📈 Distribución por categoría:")
            for cat, count, total in category_stats:
                print(f"  • {cat}: {count} transacciones (${total:,.0f})")

        conn.close()
        print(f"\n✅ Verificación completada exitosamente")

    except Exception as e:
        print(f"❌ Error verificando base de datos: {e}")
        import traceback
        traceback.print_exc()


def fix_database_permissions():
    """Intenta corregir problemas de permisos"""
    print("\n🔧 INTENTANDO CORRECCIONES...")

    # Determinar el directorio correcto
    current_dir = Path.cwd()
    if current_dir.name == 'app':
        project_root = current_dir.parent
    elif (current_dir / 'app').exists():
        project_root = current_dir
    else:
        project_root = current_dir

    db_path = project_root / "data" / "finance_app.db"
    data_dir = project_root / "data"

    # Crear directorio si no existe
    data_dir.mkdir(exist_ok=True)
    print(f"✅ Directorio data/ creado/verificado: {data_dir}")

    # Si la BD no existe, crear una básica
    if not db_path.exists():
        try:
            conn = sqlite3.connect(db_path)
            conn.execute("CREATE TABLE test (id INTEGER)")
            conn.commit()
            conn.close()
            print(f"✅ Base de datos básica creada: {db_path}")

            # Eliminar tabla de prueba
            conn = sqlite3.connect(db_path)
            conn.execute("DROP TABLE test")
            conn.commit()
            conn.close()

        except Exception as e:
            print(f"❌ No se pudo crear BD: {e}")
    else:
        print(f"✅ Base de datos ya existe: {db_path}")


if __name__ == "__main__":
    verify_database()
    print("\n" + "=" * 50)
    fix_database_permissions()