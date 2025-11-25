import os
import mysql.connector
from mysql.connector import Error
from typing import Optional, Dict, Any
from datetime import datetime
import json
from dotenv import load_dotenv

load_dotenv()

class DatabaseStorage:
    def __init__(self):
        self.host = os.getenv("DB_HOST")
        self.user = os.getenv("DB_USER")
        self.password = os.getenv("DB_PASSWORD")
        self.database = os.getenv("DB_NAME")
        self.port = int(os.getenv("DB_PORT") or 3306)
        self.connection = None
        
    def _get_connection(self, include_db: bool = True):
        """Cria conexão com o MySQL"""
        try:
            if include_db:
                conn = mysql.connector.connect(
                    host=self.host,
                    user=self.user,
                    password=self.password,
                    database=self.database,
                    port=self.port
                )
            else:
                conn = mysql.connector.connect(
                    host=self.host,
                    user=self.user,
                    password=self.password,
                    port=self.port
                )
            return conn
        except Error as e:
            print(f"Erro ao conectar ao MySQL: {e}")
            return None

    def check_connection(self) -> bool:
        """Verifica se consegue conectar ao banco"""
        conn = self._get_connection(include_db=False)
        if conn and conn.is_connected():
            conn.close()
            return True
        return False

    def create_database(self) -> bool:
        """Cria o banco de dados se não existir"""
        try:
            conn = self._get_connection(include_db=False)
            if not conn:
                return False
            
            cursor = conn.cursor()
            cursor.execute(f"CREATE DATABASE IF NOT EXISTS {self.database}")
            print(f"✓ Banco de dados '{self.database}' verificado/criado")
            cursor.close()
            conn.close()
            return True
        except Error as e:
            print(f"Erro ao criar banco de dados: {e}")
            return False

    def create_tables(self) -> bool:
        """Cria as tabelas se não existirem"""
        try:
            conn = self._get_connection()
            if not conn:
                return False
            
            cursor = conn.cursor()
            
            # Tabela webhook
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS webhook (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    date DATETIME DEFAULT CURRENT_TIMESTAMP,
                    json JSON NOT NULL
                )
            """)
            print("✓ Tabela 'webhook' verificada/criada")
            
            # Tabela contacts
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS contacts (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    wa_id VARCHAR(50) UNIQUE NOT NULL,
                    profile TEXT,
                    name VARCHAR(255),
                    create_in DATETIME DEFAULT CURRENT_TIMESTAMP,
                    last_message DATETIME
                )
            """)
            print("✓ Tabela 'contacts' verificada/criada")
            
            conn.commit()
            cursor.close()
            conn.close()
            return True
        except Error as e:
            print(f"Erro ao criar tabelas: {e}")
            return False

    def initialize(self) -> bool:
        """Inicializa o banco de dados completo"""
        print("Inicializando banco de dados...")
        
        if not self.check_connection():
            print("✗ Não foi possível conectar ao MySQL")
            return False
        print("✓ Conexão com MySQL estabelecida")
        
        if not self.create_database():
            print("✗ Erro ao criar/verificar banco de dados")
            return False
        
        if not self.create_tables():
            print("✗ Erro ao criar/verificar tabelas")
            return False
        
        print("✓ Banco de dados inicializado com sucesso!")
        return True

    def save_webhook(self, webhook_data: Dict[str, Any]) -> Optional[int]:
        """Salva o payload do webhook completo"""
        try:
            conn = self._get_connection()
            if not conn:
                return None
            
            cursor = conn.cursor()
            query = "INSERT INTO webhook (json) VALUES (%s)"
            cursor.execute(query, (json.dumps(webhook_data),))
            conn.commit()
            
            webhook_id = cursor.lastrowid
            cursor.close()
            conn.close()
            
            print(f"✓ Webhook salvo com ID: {webhook_id}")
            return webhook_id
        except Error as e:
            print(f"Erro ao salvar webhook: {e}")
            return None

    def save_or_update_contact(self, wa_id: str, name: str, profile: Optional[str] = None) -> bool:
        """Salva ou atualiza um contato"""
        try:
            conn = self._get_connection()
            if not conn:
                return False
            
            cursor = conn.cursor()
            
            # Verifica se contato existe
            cursor.execute("SELECT id FROM contacts WHERE wa_id = %s", (wa_id,))
            exists = cursor.fetchone()
            
            if exists:
                # Atualiza
                query = """
                    UPDATE contacts 
                    SET name = %s, profile = %s, last_message = %s 
                    WHERE wa_id = %s
                """
                cursor.execute(query, (name, profile, datetime.now(), wa_id))
                print(f"✓ Contato {wa_id} atualizado")
            else:
                # Insere
                query = """
                    INSERT INTO contacts (wa_id, name, profile, last_message) 
                    VALUES (%s, %s, %s, %s)
                """
                cursor.execute(query, (wa_id, name, profile, datetime.now()))
                print(f"✓ Contato {wa_id} criado")
            
            conn.commit()
            cursor.close()
            conn.close()
            return True
        except Error as e:
            print(f"Erro ao salvar/atualizar contato: {e}")
            return False

# Instância global
db = DatabaseStorage()