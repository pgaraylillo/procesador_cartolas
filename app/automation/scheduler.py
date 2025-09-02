# app/automation/scheduler.py
import schedule
import time
import logging
from pathlib import Path


class AutomationScheduler:
    """Automatiza tareas recurrentes"""

    def __init__(self, data_dir: Path):
        self.data_dir = data_dir
        self.logger = logging.getLogger(__name__)

    def setup_daily_tasks(self):
        """Configura tareas diarias"""
        # Backup de datos
        schedule.every().day.at("02:00").do(self.backup_data)

        # Limpieza de archivos temporales
        schedule.every().day.at("03:00").do(self.cleanup_temp_files)

        # Reentrenamiento semanal del modelo
        schedule.every().sunday.at("04:00").do(self.retrain_model)

    def backup_data(self):
        """Backup automático de datos"""
        try:
            backup_dir = self.data_dir / 'backups' / datetime.now().strftime('%Y-%m-%d')
            backup_dir.mkdir(parents=True, exist_ok=True)

            # Copiar archivos importantes
            for file_path in self.data_dir.glob('*.csv'):
                shutil.copy2(file_path, backup_dir)

            self.logger.info(f"Backup completed: {backup_dir}")
        except Exception as e:
            self.logger.error(f"Backup failed: {e}")

    def cleanup_temp_files(self):
        """Limpia archivos temporales antiguos"""
        try:
            uploads_dir = Path('uploads')
            if uploads_dir.exists():
                # Eliminar archivos de más de 7 días
                cutoff_date = datetime.now() - timedelta(days=7)

                for file_path in uploads_dir.iterdir():
                    if file_path.is_file():
                        file_time = datetime.fromtimestamp(file_path.stat().st_mtime)
                        if file_time < cutoff_date:
                            file_path.unlink()

            self.logger.info("Temp files cleanup completed")
        except Exception as e:
            self.logger.error(f"Cleanup failed: {e}")