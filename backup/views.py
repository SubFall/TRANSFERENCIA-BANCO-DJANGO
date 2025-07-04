from django.shortcuts import render, redirect
from django.http import FileResponse, Http404
from django.urls import reverse
from .forms import BackpForm
from .utils import ConexaoFirebird
from .models import DatabaseProcessing
import os
import fdb
import shutil # Para copiar arquivos

# A função de processamento principal (ajustaremos ela em seguida)
def process_uploaded_firebird_dbs(source_filepath: str, 
                                  destination_filepath: str, 
                                  tables_to_migrate: list):
    """
    Processa um arquivo .fdb de origem para atualizar um arquivo .fdb de destino.
    Retorna True se o processo for bem-sucedido, False caso contrário.
    """
    print(f"Iniciando processamento da origem: {source_filepath} para destino: {destination_filepath}")

    firebird_user = "SYSDBA"
    firebird_password = "masterkey" 
    
    origem_conn = None
    destino_conn = None
    try:
        # Verifica se os arquivos existem antes de tentar conectar
        if not os.path.exists(source_filepath):
            print(f"Erro: Arquivo de origem não encontrado em {source_filepath}")
            return False
        if not os.path.exists(destination_filepath):
            print(f"Erro: Arquivo de destino não encontrado em {destination_filepath}")
            return False
        
        # Conexão com o banco de dados Firebird de ORIGEM (o arquivo enviado)
        origem_conn = ConexaoFirebird(
            database=source_filepath,
            user=firebird_user,
            password=firebird_password,
            host= None # É um arquivo local
        )

        # Conexão com o banco de dados Firebird de DESTINO (o outro arquivo enviado)
        destino_conn = ConexaoFirebird(
            database=destination_filepath,
            user=firebird_user,
            password=firebird_password,
            host=None # É um arquivo local
        )

        for nome_tabela in tables_to_migrate:
            print(f'Iniciando a transferência da tabela {nome_tabela}...')

            try:
                campos = origem_conn.obter_campos_tabela(nome_tabela)
                select_query = f"SELECT {', '.join(campos)} FROM {nome_tabela}"
                dados_origem = origem_conn.executar_select(select_query)

                if not dados_origem:
                    print(f'Nenhum dado encontrado na tabela {nome_tabela}. Pulando.')
                    continue 
                
                chave_primaria = campos[0] 
                placeholders = ', '.join(['?'] * len(campos))
                insert_or_update_query_firebird = f'''
                    UPDATE OR INSERT INTO {nome_tabela} ({', '.join(campos)}) 
                    VALUES ({placeholders})
                    MATCHING({chave_primaria})
                '''
                destino_conn.executar_insert_or_update(insert_or_update_query_firebird, dados_origem)
                print(f"Transferência da tabela {nome_tabela} concluída com sucesso.")

            except fdb.Error as e_table:
                print(f"Erro ao processar a tabela {nome_tabela}: {e_table}")
                # Decide se continua ou aborta
                continue 

        print("Processamento do Firebird concluído.")
        return True

    except fdb.Error as e:
        print(f"Erro no processo de migração principal do Firebird: {e}")
    except Exception as e:
        print(f"Erro inesperado: {e}")
    finally:
        if origem_conn:
            origem_conn.fechar()
        if destino_conn:
            destino_conn.fechar()
    
    return False # Retorna False se houver falha


def upload_process_download(request):
    mensagem = ''
    processamento_id = None # Para passar o ID do registro para o link de download
    
    if request.method == 'POST':
        form = BackpForm(request.POST, request.FILES) 
        print(request.FILES)
        if form.is_valid():
            # Salva os dois arquivos no sistema de arquivos e cria o registro no DB
            processamento_instance = form.save(commit=False) # Não salva ainda para poder manipular
            
            processamento_instance.save() # Salva a instância e os arquivos são salvos em disco
            mensagem = 'Arquivos enviados com sucesso! Iniciando processamento...'

            source_filepath = processamento_instance.source_bank.path
            destination_filepath = processamento_instance.destination_bank.path
            
            # Excluir aquivos antigos
            antigos_processamentos = DatabaseProcessing.objects.exclude(pk=processamento_instance.pk).filter(processed=True)

            for old_instance in antigos_processamentos:
                print(f"Limpando arquivos antigos do registro ID: {old_instance.pk}")

                if os.path.exists(old_instance.source_bank.path):
                    os.remove(old_instance.source_bank.path)
                    print(f"  - Arquivo de origem removido: {old_instance.source_bank.path}")

                if os.path.exists(old_instance.destination_bank.path):
                    os.remove(old_instance.destination_bank.path)
                    print(f"  - Arquivo de destino removido: {old_instance.destination_bank.path}")

                if os.path.exists(old_instance.final_destination_path):
                    os.remove(old_instance.final_destination_path)
                    print(f"  - Arquivo de destino final removido: {old_instance.final_destination_path}")

                old_instance.delete()

            # copia do arquivo de destino para não sobrescrever o original
            temp_destination_path = os.path.join(
                os.path.dirname(destination_filepath), 
                f"temp_updated_{os.path.basename(destination_filepath)}"
            )
            shutil.copy(destination_filepath, temp_destination_path)
            print(f"Copiado destino original para trabalhar em: {temp_destination_path}")

            # Define as tabelas que você quer migrar
            tabelas_para_migrar = [
        'PESSOAS', 
        'PRODUTOS', 
        'PRODUTO_CODIGOS', 
        'FAMILIAS_PRODUTOS', 
        'GRUPOS_PRODUTOS',
        'SUB_GRUPOS_PRODUTOS', 
        'PRODUTO_LINKADO', 
        'USUARIOS', 
        #'USUARIOS_EMPRESAS', 
        'PROMOCAO',
        'PROMOCAO_VINCULOS', 
        'PROMOCAO_BASECALCULO', 
        'PROMOCAO_EMPRESA', 
        'PROMOCAO_PAGAMENTO',
        'PROMOCAO_TABELAPRECO', 
        'GRUPOS', 
        'FORMAS_PAGAMENTO', 
        'FORMAS_PAGAMENTO_OPE',
        'REGRAS_CASHBACK_DETALHES', 
        'PAGAMENTO_POSTERIOR', 
        'CONDICOES_PAGAMENTO',
        'CP_DETALHE', 
        'CP_DETALHE_PAGAMENTO', 
        'CP_DETALHE_PARC', 
        'CAIXA_GERAL', 
        'EMPRESAS',
        'ENDERECOS', 'CIDADES', 'ESTADOS', 
        'CARGOS', 
        'PLANO_CONTAS', 
        'PORTADORES', 
        #'TRIBUTACAO_FEDERAL',
        #TRIBUTACAO_ESTADUAL', 
        #'TABELA_NCM', 
        #'NCM',
    ] # Personalize esta lista!

            # Chama a função de processamento
            processamento_sucesso = process_uploaded_firebird_dbs(
                source_filepath, 
                temp_destination_path, # Passa o caminho da cópia temporária
                tabelas_para_migrar
            )

            if processamento_sucesso:
                mensagem += " Banco de destino atualizado com sucesso!"
                processamento_instance.processed = True
                processamento_instance.final_destination_path = temp_destination_path # Salva o caminho do arquivo processado
                processamento_instance.save() # Salva o estado atualizado
                processamento_id = processamento_instance.id # Para usar no link de download

            else:
                mensagem += " Ocorreu um erro ao atualizar o banco de destino."
                # Se falhou, remova a cópia temporária se ela foi criada
                if os.path.exists(temp_destination_path):
                    os.remove(temp_destination_path)

    else:
        form = BackpForm()
    
    return render(request, 'index.html', {
        'form': form, 
        'mensagem': mensagem,
        'processamento_id': processamento_id # Passa o ID para o template
    })

def download_processed_db(request, processamento_id):
    """
    View para permitir o download do banco de dados Firebird atualizado.
    """
    try:
        processamento_instance = DatabaseProcessing.objects.get(pk=processamento_id, processed=True)
    except BackpForm.DoesNotExist:
        raise Http404("Processamento não encontrado ou não finalizado.")

    file_path = processamento_instance.final_destination_path

    if file_path and os.path.exists(file_path):
        try:
            response = FileResponse(open(file_path, 'rb'), content_type='application/octet-stream')
            response['Content-Disposition'] = f'attachment; filename="{os.path.basename(file_path)}"'

            return response
        except Exception as e:
            print(f"Erro ao servir arquivo para download: {e}")
            raise Http404("Erro ao preparar o arquivo para download.")
    else:
        raise Http404("Arquivo de banco de dados processado não encontrado.")