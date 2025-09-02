# app/repositories/transaction_repository.py
class TransactionRepository(BaseRepository):
    def __init__(self, db_connection):
        self.db = db_connection

    def find_by_date_range(self, start_date: str, end_date: str) -> List[Dict]:
        query = """
        SELECT * FROM transactions 
        WHERE date BETWEEN ? AND ? 
        ORDER BY date DESC
        """
        return self.db.execute(query, (start_date, end_date)).fetchall()

    def find_by_category(self, category: str) -> List[Dict]:
        query = "SELECT * FROM transactions WHERE category = ?"
        return self.db.execute(query, (category,)).fetchall()

    def get_monthly_summary(self, year: int, month: int) -> Dict:
        query = """
        SELECT 
            COUNT(*) as transaction_count,
            SUM(CASE WHEN amount > 0 THEN amount ELSE 0 END) as total_income,
            SUM(CASE WHEN amount < 0 THEN amount ELSE 0 END) as total_expenses
        FROM transactions 
        WHERE strftime('%Y-%m', date) = ?
        """
        result = self.db.execute(query, (f"{year:04d}-{month:02d}",)).fetchone()
        return dict(result) if result else {}