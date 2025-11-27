import os
import mysql.connector
from mysql.connector import Error
from typing import Optional, Dict, Any, List
from datetime import datetime
import json
from dotenv import load_dotenv
import bcrypt
import random
import string

load_dotenv()

class DatabaseStorage:
    def __init__(self):
        self.host = os.getenv("DB_HOST")
        self.user = os.getenv("DB_USER")
        self.password = os.getenv("DB_PASSWORD")
        self.database = os.getenv("DB_NAME")
        self.port = int(os.getenv("DB_PORT") or 3306)
        self.connection = None
        
    def _hash_password(self, password: str) -> str:
        """Criptografa a senha usando bcrypt"""
        return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    
    def _verify_password(self, password: str, hashed: str) -> bool:
        """Verifica se a senha corresponde ao hash"""
        return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))
        
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
            
            # Tabela users
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    name VARCHAR(255) NOT NULL,
                    create_in DATETIME DEFAULT CURRENT_TIMESTAMP,
                    email VARCHAR(255) UNIQUE NOT NULL,
                    password VARCHAR(255) NOT NULL,
                    activate BOOLEAN DEFAULT TRUE
                )
            """)
            print("✓ Tabela 'users' verificada/criada")
            
            # Verifica e insere usuário padrão
            cursor.execute("SELECT COUNT(*) FROM users")
            user_count = cursor.fetchone()[0]
            
            if user_count == 0:
                # Hash da senha padrão
                hashed_password = self._hash_password('juca')
                cursor.execute("""
                    INSERT INTO users (name, email, password, activate) 
                    VALUES (%s, %s, %s, %s)
                """, ('juca_root', 'juca@juca.com', hashed_password, True))
                user_id = cursor.lastrowid
                print(f"✓ Usuário padrão 'juca_root' criado com ID: {user_id}")
                print(f"  └─ Email: juca@juca.com | Senha: juca")
            else:
                cursor.execute("SELECT id FROM users WHERE email = 'juca@juca.com' LIMIT 1")
                result = cursor.fetchone()
                user_id = result[0] if result else None

            # Tabela organization
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS organization (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    create_in DATETIME DEFAULT CURRENT_TIMESTAMP,
                    activate BOOLEAN DEFAULT TRUE,
                    create_by INT NULL,
                    organization_name VARCHAR(255) NOT NULL,
                    FOREIGN KEY (create_by) REFERENCES users(id) ON DELETE SET NULL
                )
            """)
            print("✓ Tabela 'organization' verificada/criada")

            # Tabela associativa organization_users
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS organization_users (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    organization_id INT NOT NULL,
                    user_id INT NOT NULL,
                    create_in DATETIME DEFAULT CURRENT_TIMESTAMP,
                    role ENUM('user','user_admin','user_creator') DEFAULT 'user',
                    activate BOOLEAN DEFAULT TRUE,
                    FOREIGN KEY (organization_id) REFERENCES organization(id) ON DELETE CASCADE,
                    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
                    UNIQUE KEY uniq_org_user (organization_id, user_id)
                )
            """)
            print("✓ Tabela 'organization_users' verificada/criada")
            
            # Verifica e insere organização padrão
            cursor.execute("SELECT COUNT(*) FROM organization")
            org_count = cursor.fetchone()[0]
            
            if org_count == 0:
                cursor.execute("""
                    INSERT INTO organization (organization_name, activate, create_by) 
                    VALUES (%s, %s, %s)
                """, ('juca', True, user_id))
                org_id = cursor.lastrowid
                print(f"✓ Organização padrão 'juca' criada com ID: {org_id}")
                if user_id:
                    print(f"  └─ Criada pelo usuário ID: {user_id}")
                    # Vincula criador como user_creator na organization_users
                    cursor.execute("""
                        INSERT IGNORE INTO organization_users (organization_id, user_id, role, activate)
                        VALUES (%s, %s, %s, %s)
                    """, (org_id, user_id, 'user_creator', True))
                    print("  └─ Usuário vinculado como 'user_creator'")
            else:
                cursor.execute("SELECT id FROM organization WHERE organization_name = 'juca' LIMIT 1")
                result = cursor.fetchone()
                org_id = result[0] if result else 1
                # Garante vínculo caso não exista
                if user_id and org_id:
                    cursor.execute("""
                        INSERT IGNORE INTO organization_users (organization_id, user_id, role, activate)
                        VALUES (%s, %s, %s, %s)
                    """, (org_id, user_id, 'user_creator', True))
            # Tabela webhook
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS webhook (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    date DATETIME DEFAULT CURRENT_TIMESTAMP,
                    json JSON NOT NULL
                )
            """)
            print("✓ Tabela 'webhook' verificada/criada")
            
            # Tabela contacts - CHAVE COMPOSTA (wa_id + create_for_phone_number)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS contacts (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    wa_id VARCHAR(50) NOT NULL,
                    profile VARCHAR(50) DEFAULT 'human',
                    name VARCHAR(255),
                    create_in DATETIME DEFAULT CURRENT_TIMESTAMP,
                    activate_bot BOOLEAN DEFAULT FALSE,
                    activate_automatic_message BOOLEAN DEFAULT FALSE,
                    create_for_phone_number VARCHAR(50) NOT NULL,
                    last_message_timestamp BIGINT,
                    UNIQUE KEY unique_conversation (wa_id, create_for_phone_number)
                )
            """)
            print("✓ Tabela 'contacts' verificada/criada")
            
            # Tabela settings (com FK para organization)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS settings (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    default_bot VARCHAR(50),
                    default_profile VARCHAR(50) DEFAULT 'human',
                    wa_id VARCHAR(50),
                    phone_number_id VARCHAR(50),
                    webhook_verify_token VARCHAR(255),
                    meta_token TEXT,
                    organization_id INT NULL,
                    FOREIGN KEY (organization_id) REFERENCES organization(id) ON DELETE SET NULL
                )
            """)
            print("✓ Tabela 'settings' verificada/criada")
            
            # Insere settings padrão se não existir
            cursor.execute("SELECT COUNT(*) FROM settings")
            count = cursor.fetchone()[0]
            
            if count == 0:
                meta_token = os.getenv("META_TOKEN", None)
                cursor.execute("""
                    INSERT INTO settings 
                    (default_bot, default_profile, wa_id, phone_number_id, webhook_verify_token, meta_token, organization_id) 
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                """, (None, 'human', '556181412286', '524386454098961', '7b5a67574d8b1d77d2803b24946950f0', meta_token, org_id))
                print(f"✓ Configuração padrão inserida e vinculada à organização ID: {org_id}")
            
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

    # ==================== WEBHOOK ====================
    
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

    # ==================== CONTACTS ====================
    
    def save_or_update_contact(
        self, 
        wa_id: str, 
        name: str,
        phone_number_id: str,
        timestamp: int
    ) -> bool:
        """Salva ou atualiza um contato com base nas configurações"""
        try:
            conn = self._get_connection()
            if not conn:
                return False
            
            cursor = conn.cursor(dictionary=True)
            
            # Busca configurações do número
            cursor.execute(
                "SELECT default_profile FROM settings WHERE phone_number_id = %s", 
                (phone_number_id,)
            )
            settings = cursor.fetchone()
            
            # Define profile e activate_bot baseado nas settings
            if settings:
                profile = settings.get('default_profile', 'human')
                activate_bot = False if profile == 'human' else True
            else:
                profile = 'human'
                activate_bot = False
            
            # Verifica se ESTA CONVERSA ESPECÍFICA existe (wa_id + phone_number_id)
            cursor.execute(
                "SELECT id, create_in FROM contacts WHERE wa_id = %s AND create_for_phone_number = %s", 
                (wa_id, phone_number_id)
            )
            contact = cursor.fetchone()
            
            if contact:
                # Conversa já existe - atualiza
                query = """
                    UPDATE contacts 
                    SET name = %s, last_message_timestamp = %s 
                    WHERE wa_id = %s AND create_for_phone_number = %s
                """
                cursor.execute(query, (name, timestamp, wa_id, phone_number_id))
                
                first_message_date = contact['create_in'].strftime('%d/%m/%Y %H:%M:%S')
                print(f"✓ Contato {wa_id} ({name}) atualizado")
                print(f"  └─ Conversa com número: {phone_number_id}")
                print(f"  └─ Primeira mensagem desta conversa foi em: {first_message_date}")
                print(f"  └─ Esta é mais uma mensagem nesta conversa")
            else:
                # Nova conversa - insere
                query = """
                    INSERT INTO contacts 
                    (wa_id, name, profile, create_for_phone_number, last_message_timestamp, activate_bot, activate_automatic_message) 
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                """
                cursor.execute(query, (
                    wa_id, 
                    name, 
                    profile, 
                    phone_number_id, 
                    timestamp, 
                    activate_bot, 
                    False
                ))
                
                now = datetime.now().strftime('%d/%m/%Y %H:%M:%S')
                print(f"✓ Nova conversa criada: {wa_id} ({name}) → {phone_number_id}")
                print(f"  └─ Esta é a PRIMEIRA mensagem desta conversa")
                print(f"  └─ Criado em: {now}")
                print(f"  └─ Profile: {profile}")
                print(f"  └─ Bot ativado: {activate_bot}")
            
            conn.commit()
            cursor.close()
            conn.close()
            return True
        except Error as e:
            print(f"Erro ao salvar/atualizar contato: {e}")
            return False

    # ==================== SETTINGS ====================
    
    def get_settings(self, phone_number_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Busca as configurações do sistema"""
        try:
            conn = self._get_connection()
            if not conn:
                return None
            
            cursor = conn.cursor(dictionary=True)
            
            if phone_number_id:
                cursor.execute(
                    "SELECT * FROM settings WHERE phone_number_id = %s", 
                    (phone_number_id,)
                )
            else:
                cursor.execute("SELECT * FROM settings WHERE id = 1")
            
            settings = cursor.fetchone()
            
            cursor.close()
            conn.close()
            return settings
        except Error as e:
            print(f"Erro ao buscar configurações: {e}")
            return None

    # ==================== ORGANIZATION ====================
    
    def create_organization(self, organization_name: str, create_by: Optional[int] = None) -> Optional[Dict[str, Any]]:
        """Cria organização e vincula criador como user_creator"""
        try:
            conn = self._get_connection()
            if not conn:
                return None
            cur = conn.cursor(dictionary=True)

            cur.execute("""
                INSERT INTO organization (organization_name, activate, create_by)
                VALUES (%s, %s, %s)
            """, (organization_name, True, create_by))
            org_id = cur.lastrowid

            # Vincula criador como user_creator
            if create_by:
                cur.execute("""
                    INSERT IGNORE INTO organization_users (organization_id, user_id, role, activate)
                    VALUES (%s, %s, %s, %s)
                """, (org_id, create_by, 'user_creator', True))

            conn.commit()

            cur.execute("SELECT * FROM organization WHERE id = %s", (org_id,))
            org = cur.fetchone()

            cur.close()
            conn.close()
            return org
        except Error as e:
            print(f"Erro ao criar organização: {e}")
            return None

    def deactivate_organization(self, org_id: int) -> Optional[Dict[str, Any]]:
        """Desativa organização"""
        try:
            conn = self._get_connection()
            if not conn:
                return None
            cur = conn.cursor(dictionary=True)
            cur.execute("UPDATE organization SET activate = FALSE WHERE id = %s", (org_id,))
            conn.commit()
            cur.execute("SELECT * FROM organization WHERE id = %s", (org_id,))
            org = cur.fetchone()
            cur.close()
            conn.close()
            return org
        except Error as e:
            print(f"Erro ao desativar organização: {e}")
            return None

    def update_organization_name(self, org_id: int, new_name: str) -> Optional[Dict[str, Any]]:
        """Atualiza nome da organização"""
        try:
            conn = self._get_connection()
            if not conn:
                return None
            cur = conn.cursor(dictionary=True)
            cur.execute("UPDATE organization SET organization_name = %s WHERE id = %s", (new_name, org_id))
            conn.commit()
            cur.execute("SELECT * FROM organization WHERE id = %s", (org_id,))
            org = cur.fetchone()
            cur.close()
            conn.close()
            return org
        except Error as e:
            print(f"Erro ao atualizar nome da organização: {e}")
            return None

    # ==================== ORGANIZATION USERS ====================
    # def add_user_to_organization(self, organization_id: int, user_id: int, role: str = 'user') -> bool:
    #     """Vincula um usuário à organização com um papel."""
    #     try:
    #         if role not in ('user', 'user_admin', 'user_creator'):
    #             role = 'user'
    #         conn = self._get_connection()
    #         if not conn:
    #             return False
    #         cursor = conn.cursor()
    #         cursor.execute("""
    #             INSERT IGNORE INTO organization_users (organization_id, user_id, role, activate)
    #             VALUES (%s, %s, %s, %s)
    #         """, (organization_id, user_id, role, True))
    #         conn.commit()
    #         cursor.close()
    #         conn.close()
    #         return True
    #     except Error as e:
    #         print(f"Erro ao vincular usuário à organização: {e}")
    #         return False

    # def remove_user_from_organization(self, organization_id: int, user_id: int) -> bool:
    #     """Remove vínculo usuário-organização"""
    #     try:
    #         conn = self._get_connection()
    #         if not conn:
    #             return False
    #         cur = conn.cursor()
    #         cur.execute("DELETE FROM organization_users WHERE organization_id = %s AND user_id = %s",
    #                     (organization_id, user_id))
    #         conn.commit()
    #         cur.close()
    #         conn.close()
    #         return True
    #     except Error as e:
    #         print(f"Erro ao remover usuário da organização: {e}")
    #         return False

    # def update_organization_user_role(self, organization_id: int, user_id: int, role: str) -> Optional[Dict[str, Any]]:
    #     """Atualiza o papel do usuário na organização"""
    #     try:
    #         if role not in ('user', 'user_admin', 'user_creator'):
    #             return None
    #         conn = self._get_connection()
    #         if not conn:
    #             return None
    #         cur = conn.cursor(dictionary=True)
    #         cur.execute("""
    #             UPDATE organization_users SET role = %s WHERE organization_id = %s AND user_id = %s
    #         """, (role, organization_id, user_id))
    #         conn.commit()
    #         cur.execute("""
    #             SELECT * FROM organization_users WHERE organization_id = %s AND user_id = %s
    #         """, (organization_id, user_id))
    #         row = cur.fetchone()
    #         cur.close()
    #         conn.close()
    #         return row
    #     except Error as e:
    #         print(f"Erro ao atualizar role do usuário: {e}")
    #         return None

    # def set_organization_user_active(self, organization_id: int, user_id: int, active: bool) -> Optional[Dict[str, Any]]:
    #     """Ativa/Desativa o vínculo do usuário com a organização"""
    #     try:
    #         conn = self._get_connection()
    #         if not conn:
    #             return None
    #         cur = conn.cursor(dictionary=True)
    #         cur.execute("""
    #             UPDATE organization_users SET activate = %s WHERE organization_id = %s AND user_id = %s
    #         """, (active, organization_id, user_id))
    #         conn.commit()
    #         cur.execute("""
    #             SELECT * FROM organization_users WHERE organization_id = %s AND user_id = %s
    #         """, (organization_id, user_id))
    #         row = cur.fetchone()
    #         cur.close()
    #         conn.close()
    #         return row
    #     except Error as e:
    #         print(f"Erro ao atualizar ativação do usuário na organização: {e}")
    #         return None

    def list_organization_users(self, organization_id: int) -> List[Dict[str, Any]]:
        """Lista usuários vinculados a uma organização."""
        try:
            conn = self._get_connection()
            if not conn:
                return []
            cursor = conn.cursor(dictionary=True)
            cursor.execute("""
                SELECT ou.id, ou.organization_id, ou.user_id, ou.role, ou.activate, ou.create_in,
                       u.name, u.email
                FROM organization_users ou
                JOIN users u ON u.id = ou.user_id
                WHERE ou.organization_id = %s
            """, (organization_id,))
            rows = cursor.fetchall()
            cursor.close()
            conn.close()
            return rows
        except Error as e:
            print(f"Erro ao listar usuários da organização: {e}")
            return []

    # ==================== SETTINGS (por organização) ====================
    def create_settings(self, organization_id: int, default_bot: Optional[str], default_profile: Optional[str],
                        wa_id: Optional[str], phone_number_id: Optional[str],
                        webhook_verify_token: Optional[str], meta_token: Optional[str]) -> Optional[Dict[str, Any]]:
        """Cria settings para a organização"""
        try:
            conn = self._get_connection()
            if not conn:
                return None
            cur = conn.cursor(dictionary=True)
            cur.execute("""
                INSERT INTO settings (default_bot, default_profile, wa_id, phone_number_id, webhook_verify_token, meta_token, organization_id)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """, (default_bot, default_profile or 'human', wa_id, phone_number_id, webhook_verify_token, meta_token, organization_id))
            settings_id = cur.lastrowid
            conn.commit()
            cur.execute("SELECT * FROM settings WHERE id = %s", (settings_id,))
            row = cur.fetchone()
            cur.close()
            conn.close()
            return row
        except Error as e:
            print(f"Erro ao criar settings: {e}")
            return None

    def delete_settings(self, settings_id: int) -> bool:
        """Remove settings por ID"""
        try:
            conn = self._get_connection()
            if not conn:
                return False
            cur = conn.cursor()
            cur.execute("DELETE FROM settings WHERE id = %s", (settings_id,))
            conn.commit()
            cur.close()
            conn.close()
            return True
        except Error as e:
            print(f"Erro ao remover settings: {e}")
            return False

    # ==================== USERS ====================
    def create_user(self, name: str, email: str, password: str) -> Optional[Dict[str, Any]]:
        """Cria um novo usuário (senha com bcrypt)."""
        try:
            conn = self._get_connection()
            if not conn:
                return None
            cur = conn.cursor(dictionary=True)

            # Verifica duplicidade de email
            cur.execute("SELECT id FROM users WHERE email = %s", (email,))
            if cur.fetchone():
                cur.close()
                conn.close()
                return None

            hashed = self._hash_password(password)
            cur.execute("""
                INSERT INTO users (name, email, password, activate)
                VALUES (%s, %s, %s, %s)
            """, (name, email, hashed, True))
            user_id = cur.lastrowid
            conn.commit()

            cur.execute("SELECT id, name, email, create_in, activate FROM users WHERE id = %s", (user_id,))
            user = cur.fetchone()

            cur.close()
            conn.close()
            return user
        except Error as e:
            print(f"Erro ao criar usuário: {e}")
            return None

    def get_users(self, skip: int = 0, limit: int = 100) -> List[Dict[str, Any]]:
        """Lista usuários com paginação."""
        try:
            conn = self._get_connection()
            if not conn:
                return []
            cur = conn.cursor(dictionary=True)
            cur.execute(
                "SELECT id, name, email, create_in, activate FROM users LIMIT %s OFFSET %s",
                (limit, skip)
            )
            rows = cur.fetchall()
            cur.close()
            conn.close()
            return rows
        except Error as e:
            print(f"Erro ao buscar usuários: {e}")
            return []

    def get_user(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Busca um usuário pelo ID."""
        try:
            conn = self._get_connection()
            if not conn:
                return None
            cur = conn.cursor(dictionary=True)
            cur.execute("SELECT id, name, email, create_in, activate FROM users WHERE id = %s", (user_id,))
            row = cur.fetchone()
            cur.close()
            conn.close()
            return row
        except Error as e:
            print(f"Erro ao buscar usuário: {e}")
            return None

    def update_user_name(self, user_id: int, name: str) -> Optional[Dict[str, Any]]:
        """Atualiza o nome do usuário."""
        try:
            conn = self._get_connection()
            if not conn:
                return None
            cur = conn.cursor(dictionary=True)
            cur.execute("UPDATE users SET name = %s WHERE id = %s", (name, user_id))
            conn.commit()
            cur.execute("SELECT id, name, email, create_in, activate FROM users WHERE id = %s", (user_id,))
            row = cur.fetchone()
            cur.close()
            conn.close()
            return row
        except Error as e:
            print(f"Erro ao atualizar usuário: {e}")
            return None

    def update_user_password(self, user_id: int, password: str) -> bool:
        """Atualiza a senha do usuário (bcrypt)."""
        try:
            conn = self._get_connection()
            if not conn:
                return False
            hashed = self._hash_password(password)
            cur = conn.cursor()
            cur.execute("UPDATE users SET password = %s WHERE id = %s", (hashed, user_id))
            conn.commit()
            cur.close()
            conn.close()
            return True
        except Error as e:
            print(f"Erro ao atualizar senha: {e}")
            return False

    def deactivate_user(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Desativa a conta do usuário."""
        try:
            conn = self._get_connection()
            if not conn:
                return None
            cur = conn.cursor(dictionary=True)
            cur.execute("UPDATE users SET activate = FALSE WHERE id = %s", (user_id,))
            conn.commit()
            cur.execute("SELECT id, name, email, create_in, activate FROM users WHERE id = %s", (user_id,))
            row = cur.fetchone()
            cur.close()
            conn.close()
            return row
        except Error as e:
            print(f"Erro ao desativar usuário: {e}")
            return None

    def activate_user(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Ativa a conta do usuário."""
        try:
            conn = self._get_connection()
            if not conn:
                return None
            cur = conn.cursor(dictionary=True)
            cur.execute("UPDATE users SET activate = TRUE WHERE id = %s", (user_id,))
            conn.commit()
            cur.execute("SELECT id, name, email, create_in, activate FROM users WHERE id = %s", (user_id,))
            row = cur.fetchone()
            cur.close()
            conn.close()
            return row
        except Error as e:
            print(f"Erro ao ativar usuário: {e}")
            return None
        
    # coe 

    
    def get_organization(self, org_id: int) -> Optional[Dict[str, Any]]:
        """Busca uma organização pelo ID"""
        try:
            conn = self._get_connection()
            if not conn:
                return None
            
            cursor = conn.cursor(dictionary=True)
            cursor.execute("SELECT * FROM organization WHERE id = %s", (org_id,))
            organization = cursor.fetchone()
            
            cursor.close()
            conn.close()
            return organization
        except Error as e:
            print(f"Erro ao buscar organização: {e}")
            return None

    def get_all_organizations(self, skip: int = 0, limit: int = 100) -> List[Dict[str, Any]]:
        """Lista todas as organizações"""
        try:
            conn = self._get_connection()
            if not conn:
                return []
            cur = conn.cursor(dictionary=True)
            cur.execute("SELECT * FROM organization LIMIT %s OFFSET %s", (limit, skip))
            rows = cur.fetchall()
            cur.close()
            conn.close()
            return rows
        except Error as e:
            print(f"Erro ao listar organizações: {e}")
            return []

    def get_user_organizations(self, user_id: int) -> List[Dict[str, Any]]:
        """Lista todas as organizações que o usuário participa"""
        try:
            conn = self._get_connection()
            if not conn:
                return []
            cur = conn.cursor(dictionary=True)
            cur.execute("""
                SELECT o.*, ou.role, ou.activate as user_active_in_org, ou.create_in as joined_at
                FROM organization o
                JOIN organization_users ou ON o.id = ou.organization_id
                WHERE ou.user_id = %s
            """, (user_id,))
            rows = cur.fetchall()
            cur.close()
            conn.close()
            return rows
        except Error as e:
            print(f"Erro ao listar organizações do usuário: {e}")
            return []

    def get_organization_settings(self, organization_id: int) -> List[Dict[str, Any]]:
        """Lista todos os settings de uma organização"""
        try:
            conn = self._get_connection()
            if not conn:
                return []
            cur = conn.cursor(dictionary=True)
            cur.execute("SELECT * FROM settings WHERE organization_id = %s", (organization_id,))
            rows = cur.fetchall()
            cur.close()
            conn.close()
            return rows
        except Error as e:
            print(f"Erro ao listar settings da organização: {e}")
            return []

    # ==================== ORGANIZATION USERS (com validações) ====================
    def add_user_to_organization(self, organization_id: int, user_id: int, role: str = 'user') -> Dict[str, Any]:
        """Vincula um usuário à organização com validações"""
        try:
            if role not in ('user', 'user_admin', 'user_creator'):
                role = 'user'
            
            conn = self._get_connection()
            if not conn:
                return {"success": False, "message": "Erro ao conectar ao banco de dados"}
            
            cursor = conn.cursor(dictionary=True)
            
            # Valida se organização existe
            cursor.execute("SELECT id FROM organization WHERE id = %s", (organization_id,))
            if not cursor.fetchone():
                cursor.close()
                conn.close()
                return {"success": False, "message": f"Organização ID {organization_id} não encontrada"}
            
            # Valida se usuário existe
            cursor.execute("SELECT id FROM users WHERE id = %s", (user_id,))
            if not cursor.fetchone():
                cursor.close()
                conn.close()
                return {"success": False, "message": f"Usuário ID {user_id} não encontrado"}
            
            # Verifica se já existe vínculo
            cursor.execute("""
                SELECT id FROM organization_users 
                WHERE organization_id = %s AND user_id = %s
            """, (organization_id, user_id))
            if cursor.fetchone():
                cursor.close()
                conn.close()
                return {"success": False, "message": "Usuário já está vinculado a esta organização"}
            
            # Insere vínculo
            cursor.execute("""
                INSERT INTO organization_users (organization_id, user_id, role, activate)
                VALUES (%s, %s, %s, %s)
            """, (organization_id, user_id, role, True))
            conn.commit()
            cursor.close()
            conn.close()
            
            return {"success": True, "message": f"Usuário ID {user_id} adicionado com role '{role}'"}
        except Error as e:
            print(f"Erro ao vincular usuário à organização: {e}")
            return {"success": False, "message": f"Erro: {str(e)}"}

    def remove_user_from_organization(self, organization_id: int, user_id: int) -> Dict[str, Any]:
        """Remove vínculo com validações"""
        try:
            conn = self._get_connection()
            if not conn:
                return {"success": False, "message": "Erro ao conectar ao banco de dados"}
            
            cur = conn.cursor(dictionary=True)
            
            # Verifica se vínculo existe
            cur.execute("""
                SELECT id FROM organization_users 
                WHERE organization_id = %s AND user_id = %s
            """, (organization_id, user_id))
            if not cur.fetchone():
                cur.close()
                conn.close()
                return {"success": False, "message": f"Usuário ID {user_id} não está vinculado à organização ID {organization_id}"}
            
            # Remove vínculo
            cur.execute("""
                DELETE FROM organization_users 
                WHERE organization_id = %s AND user_id = %s
            """, (organization_id, user_id))
            conn.commit()
            cur.close()
            conn.close()
            
            return {"success": True, "message": f"Usuário ID {user_id} removido da organização"}
        except Error as e:
            print(f"Erro ao remover usuário da organização: {e}")
            return {"success": False, "message": f"Erro: {str(e)}"}

    def update_organization_user_role(self, organization_id: int, user_id: int, role: str) -> Dict[str, Any]:
        """Atualiza role com validações"""
        try:
            if role not in ('user', 'user_admin', 'user_creator'):
                return {"success": False, "message": f"Role '{role}' inválido. Use: user, user_admin ou user_creator"}
            
            conn = self._get_connection()
            if not conn:
                return {"success": False, "message": "Erro ao conectar ao banco de dados"}
            
            cur = conn.cursor(dictionary=True)
            
            # Verifica se vínculo existe
            cur.execute("""
                SELECT id FROM organization_users 
                WHERE organization_id = %s AND user_id = %s
            """, (organization_id, user_id))
            if not cur.fetchone():
                cur.close()
                conn.close()
                return {"success": False, "message": f"Usuário ID {user_id} não está vinculado à organização ID {organization_id}"}
            
            # Atualiza role
            cur.execute("""
                UPDATE organization_users SET role = %s 
                WHERE organization_id = %s AND user_id = %s
            """, (role, organization_id, user_id))
            conn.commit()
            cur.close()
            conn.close()
            
            return {"success": True, "message": f"Role do usuário ID {user_id} atualizado para '{role}'"}
        except Error as e:
            print(f"Erro ao atualizar role: {e}")
            return {"success": False, "message": f"Erro: {str(e)}"}

    def set_organization_user_active(self, organization_id: int, user_id: int, active: bool) -> Dict[str, Any]:
        """Ativa/Desativa com validações"""
        try:
            conn = self._get_connection()
            if not conn:
                return {"success": False, "message": "Erro ao conectar ao banco de dados"}
            
            cur = conn.cursor(dictionary=True)
            
            # Verifica se vínculo existe
            cur.execute("""
                SELECT id FROM organization_users 
                WHERE organization_id = %s AND user_id = %s
            """, (organization_id, user_id))
            if not cur.fetchone():
                cur.close()
                conn.close()
                return {"success": False, "message": f"Usuário ID {user_id} não está vinculado à organização ID {organization_id}"}
            
            # Atualiza status
            cur.execute("""
                UPDATE organization_users SET activate = %s 
                WHERE organization_id = %s AND user_id = %s
            """, (active, organization_id, user_id))
            conn.commit()
            cur.close()
            conn.close()
            
            status_text = "ativado" if active else "desativado"
            return {"success": True, "message": f"Usuário ID {user_id} {status_text} na organização"}
        except Error as e:
            print(f"Erro ao atualizar ativação: {e}")
            return {"success": False, "message": f"Erro: {str(e)}"}

    def reset_user_password(self, email: str) -> Dict[str, Any]:
        """Reseta a senha do usuário e retorna a nova senha"""
        try:
            conn = self._get_connection()
            if not conn:
                return {"success": False, "message": "Erro ao conectar ao banco de dados"}
            
            cur = conn.cursor(dictionary=True)
            
            # Verifica se email existe e usuário está ativo
            cur.execute("SELECT id, name, email, activate FROM users WHERE email = %s", (email,))
            user = cur.fetchone()
            
            if not user:
                cur.close()
                conn.close()
                return {"success": False, "message": f"Email {email} não encontrado"}
            
            if not user['activate']:
                cur.close()
                conn.close()
                return {"success": False, "message": "Usuário desativado. Entre em contato com o suporte."}
            
            # Gera senha numérica aleatória de 8 dígitos
            new_password = ''.join(random.choices(string.digits, k=8))
            
            # Hash da nova senha
            hashed = self._hash_password(new_password)
            
            # Atualiza senha
            cur.execute("UPDATE users SET password = %s WHERE id = %s", (hashed, user['id']))
            conn.commit()
            cur.close()
            conn.close()
            
            return {
                "success": True, 
                "message": "Senha resetada com sucesso",
                "user_id": user['id'],
                "name": user['name'],
                "email": user['email'],
                "new_password": new_password
            }
        except Error as e:
            print(f"Erro ao resetar senha: {e}")
            return {"success": False, "message": f"Erro: {str(e)}"}

    def authenticate_user(self, email: str, password: str) -> Optional[Dict[str, Any]]:
        """Autentica usuário por email e senha"""
        try:
            conn = self._get_connection()
            if not conn:
                return None
            
            cur = conn.cursor(dictionary=True)
            
            # Busca usuário por email
            cur.execute("SELECT id, name, email, password, activate FROM users WHERE email = %s", (email,))
            user = cur.fetchone()
            
            cur.close()
            conn.close()
            
            if not user:
                return None
            
            # Verifica se usuário está ativo
            if not user['activate']:
                return None
            
            # Verifica senha
            if not self._verify_password(password, user['password']):
                return None
            
            # Remove senha do retorno
            del user['password']
            return user
            
        except Error as e:
            print(f"Erro ao autenticar usuário: {e}")
            return None

# Instância global
db = DatabaseStorage()