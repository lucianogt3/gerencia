import os
import shutil

# Define o caminho da pasta problemática
caminho_scales = os.path.join(os.getcwd(), "app", "blueprints", "scales")
arquivo_init = os.path.join(caminho_scales, "__init__.py")
pasta_cache = os.path.join(caminho_scales, "__pycache__")

print(f"🕵️‍♂️ ANALISANDO A PASTA: {caminho_scales}\n")

if os.path.exists(caminho_scales):
    
    # 1. APAGAR O CACHE (Memória antiga)
    if os.path.exists(pasta_cache):
        try:
            shutil.rmtree(pasta_cache)
            print("✅ Cache antigo (__pycache__) foi DELETADO com sucesso.")
        except Exception as e:
            print(f"⚠️ Não foi possível apagar o cache: {e}")
    else:
        print("✅ Nenhum cache antigo encontrado.")

    # 2. LIMPAR O ARQUIVO __INIT__.PY (O culpado)
    if os.path.exists(arquivo_init):
        print(f"found __init__.py em: {arquivo_init}")
        try:
            # Abre o arquivo e apaga tudo dentro dele
            with open(arquivo_init, "w") as f:
                f.write("") # Deixa vazio
            print("✅ Arquivo __init__.py foi LIMPO (Código antigo removido).")
        except Exception as e:
            print(f"❌ Erro ao limpar __init__.py: {e}")
    else:
        # Se não existir, cria um vazio para garantir
        with open(arquivo_init, "w") as f:
            f.write("")
        print("✅ Arquivo __init__.py não existia, foi CRIADO vazio.")

    print("\n🎉 LIMPEZA CONCLUÍDA! Tente rodar o servidor agora.")

else:
    print(f"❌ ERRO: A pasta {caminho_scales} não foi encontrada. Verifique se você está na raiz do projeto.")