import pandas as pd
from typing import Dict, List, Optional, Any, Tuple, Union
from sqlalchemy import text
from app.db.base import db_handler


class QueryExecutor:
    """
    Class để thực thi các truy vấn SQL thuần
    """
    
    def __init__(self, db_name: str = "default"):
        self.db_name = db_name
        self.db_handler = db_handler
    
    def execute_query(self, query: str, params: Optional[Dict] = None) -> List[Dict]:
        """
        Thực thi SELECT query và trả về list of dictionaries
        
        Args:
            query: SQL query string
            params: Dictionary các parameters cho query
            
        Returns:
            List[Dict]: Kết quả query
        """
        with self.db_handler.get_session(self.db_name) as session:
            result = session.execute(text(query), params or {})
            columns = result.keys()
            return [dict(zip(columns, row)) for row in result.fetchall()]
    
    def execute_query_pandas(self, query: str, params: Optional[Dict] = None) -> pd.DataFrame:
        """
        Thực thi SELECT query và trả về pandas DataFrame
        
        Args:
            query: SQL query string
            params: Dictionary các parameters cho query
            
        Returns:
            pd.DataFrame: Kết quả query
        """
        with self.db_handler.get_session(self.db_name) as session:
            return pd.read_sql(text(query), session.bind, params=params)
    
    def execute_command(self, query: str, params: Optional[Dict] = None) -> int:
        """
        Thực thi INSERT/UPDATE/DELETE command
        
        Args:
            query: SQL command string
            params: Dictionary các parameters cho command
            
        Returns:
            int: Số rows affected
        """
        with self.db_handler.get_session(self.db_name) as session:
            result = session.execute(text(query), params or {})
            session.commit()
            return result.rowcount
    
    def execute_bulk_insert(self, table: str, data: List[Dict]) -> None:
        """
        Thực hiện bulk insert
        
        Args:
            table: Tên table
            data: List of dictionaries chứa data cần insert
        """
        if not data:
            return
            
        # Tạo query dựa trên database type
        connection = self.db_handler.get_connection(self.db_name)
        
        if connection.db_type == "mysql":
            # MySQL syntax
            columns = list(data[0].keys())
            placeholders = ", ".join([f":{col}" for col in columns])
            query = f"INSERT INTO {table} ({', '.join(columns)}) VALUES ({placeholders})"
        else:
            # SQL Server syntax
            columns = list(data[0].keys())
            placeholders = ", ".join([f":{col}" for col in columns])
            query = f"INSERT INTO {table} ({', '.join(columns)}) VALUES ({placeholders})"
        
        with self.db_handler.get_session(self.db_name) as session:
            session.execute(text(query), data)
            session.commit()
    
    def execute_stored_procedure(self, procedure_name: str, params: Optional[Dict] = None) -> List[Dict]:
        """
        Thực thi stored procedure
        
        Args:
            procedure_name: Tên stored procedure
            params: Dictionary các parameters
            
        Returns:
            List[Dict]: Kết quả từ stored procedure
        """
        connection = self.db_handler.get_connection(self.db_name)
        
        if connection.db_type == "mysql":
            # MySQL CALL syntax
            if params:
                param_list = ", ".join([f":{key}" for key in params.keys()])
                query = f"CALL {procedure_name}({param_list})"
            else:
                query = f"CALL {procedure_name}()"
        else:
            # SQL Server EXEC syntax
            if params:
                param_list = ", ".join([f"@{key}=:{key}" for key in params.keys()])
                query = f"EXEC {procedure_name} {param_list}"
            else:
                query = f"EXEC {procedure_name}"
        
        return self.execute_query(query, params)
    
    def execute_transaction(self, queries: List[Tuple[str, Optional[Dict]]]) -> None:
        """
        Thực thi nhiều queries trong một transaction
        
        Args:
            queries: List of tuples (query, params)
        """
        with self.db_handler.get_session(self.db_name) as session:
            try:
                for query, params in queries:
                    session.execute(text(query), params or {})
                session.commit()
            except Exception as e:
                session.rollback()
                raise e


mysql_executor = QueryExecutor("mysql")
default_executor = QueryExecutor("default")