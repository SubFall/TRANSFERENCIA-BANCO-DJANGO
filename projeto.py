import fdb

db_origem = 'C:\\Sol.NET_BD\\SOLNET_PDV.FDB'
db_destino = 'C:\\Sol.NET_BD\\SOLNET.FDB'

class ConexaoFirebird:
    def __init__(self, host, database, user, password):
        self.conexao = fdb.connect(
            host=host,
            database=database,
            user=user,
            password=password,
            charset='win1252'
        )
    
    def executar_select(self, query):
        cursor = self.conexao.cursor()
        cursor.execute(query)
        dados = cursor.fetchall()
        cursor.close()
        return dados
    
    def obter_campos_tabela(self, nome_tabela):
        cursor = self.conexao.cursor()
        sql = f"""
            SELECT TRIM(r.RDB$FIELD_NAME)
            FROM RDB$RELATION_FIELDS r
            WHERE r.RDB$RELATION_NAME = UPPER('{nome_tabela}')
            ORDER BY r.RDB$FIELD_POSITION
        """
        cursor.execute(sql)
        campos = [linha[0] for linha in cursor.fetchall()]
        cursor.close()
        return campos
    
    def executar_insert_or_update(self, query, dados):
        cursor = self.conexao.cursor()
        cursor.executemany(query, dados)
        self.conexao.commit()
        cursor.close()
    
    def fechar(self):
        self.conexao.close()
    
def transferir_dados_origem_para_destino(origem: ConexaoFirebird, 
                                        destino: ConexaoFirebird, 
                                        nome_tabela: str):
    print(f'Iniciando a transferência da tabela {nome_tabela}...')

    # pega os campos da tabela dinamicamente
    campos = origem.obter_campos_tabela(nome_tabela)

    # Montar o SELECT 
    select_query = f"SELECT {', '.join(campos)} FROM {nome_tabela}"
    dados_origem = origem.executar_select(select_query)
    chave_primaria = campos[0]

    if not dados_origem:
        print(f'Nenhum dado encontrado na tabela {nome_tabela}')
        return   
    
    # Montar o INSERT
    placeholders = ', '.join(['?'] * len(campos))
    insert_query = f'''UPDATE OR INSERT INTO {nome_tabela} ({', '.join(campos)}) 
                        VALUES ({placeholders})
                        MATCHING({chave_primaria})'''
    
    # Executar insert ou update no destino
    destino.executar_insert_or_update(insert_query, dados_origem)

    print(f"Transferência da tabela {nome_tabela} concluída com sucesso!")

if __name__ == '__main__':
    origem = ConexaoFirebird('localhost', 
                         db_origem,
                         'SYSDBA',
                         'masterkey')
    destino = ConexaoFirebird('localhost', 
                         db_destino,
                         'SYSDBA',
                         'masterkey')

    tabelas = ['PESSOAS', 'PRODUTOS']
    for tabela in tabelas:
          transferir_dados_origem_para_destino(origem, destino, tabela)  

    origem.fechar()
    #print('Olá mundo')