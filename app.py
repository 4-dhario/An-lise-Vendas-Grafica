
import json
from streamlit_javascript import st_javascript
import streamlit as st
import pandas as pd
from supabase import create_client

st.set_page_config(
    page_title="Gestão de Gráfica",
    page_icon="",
    layout="wide"
)

st.title(" Sistema de Gestão da Gráfica")
st.caption("Gestão comercial e análise de vendas")

# Ligação à base de dados
@st.cache_resource
def obter_cliente():
    return create_client(
        st.secrets["SUPABASE_URL"],
        st.secrets["SUPABASE_KEY"]
    )

try:
    if "supabase" not in st.session_state:
        st.session_state.supabase = obter_cliente()
    sb = st.session_state.supabase
except Exception:
    st.error(
        "Não foi possível ligar ao Supabase. "
        "Confirma as variáveis SUPABASE_URL e SUPABASE_KEY "
        "nas definições Secrets do Streamlit Cloud."
    )
    st.stop()
    

# Receber o link de recuperação no navegador
if "modo_recuperacao" not in st.session_state:
    st.session_state.modo_recuperacao = False

fragmento = st_javascript("""
(() => {
    const hash = window.parent.location.hash;
    const params = new URLSearchParams(hash.slice(1));

    if (params.get("type") !== "recovery") {
        return "";
    }

    const dados = {
        type: params.get("type"),
        access_token: params.get("access_token"),
        refresh_token: params.get("refresh_token")
    };

    if (!dados.access_token || !dados.refresh_token) {
        return "";
    }

    window.parent.history.replaceState(
        null,
        "",
        window.parent.location.pathname +
        window.parent.location.search
    );

    return JSON.stringify(dados);
})()
""")

if isinstance(fragmento, str) and fragmento:
    try:
        dados_recuperacao = json.loads(fragmento)

        if (
            dados_recuperacao.get("type") == "recovery"
            and dados_recuperacao.get("access_token")
            and dados_recuperacao.get("refresh_token")
        ):
            sb.auth.set_session(
                dados_recuperacao["access_token"],
                dados_recuperacao["refresh_token"]
            )
            st.session_state.modo_recuperacao = True
            st.session_state.utilizador = None
            st.rerun()

    except Exception:
        st.error(
            "O link de recuperação é inválido ou expirou. "
            "Solicita um novo e-mail."
        )
# Autenticação

# Formulário de nova palavra-passe
if st.session_state.modo_recuperacao:
    st.subheader("Definir nova palavra-passe")

    with st.form("nova_palavra_passe"):
        nova_senha = st.text_input(
            "Nova palavra-passe",
            type="password"
        )
        confirmar_senha = st.text_input(
            "Confirmar nova palavra-passe",
            type="password"
        )
        guardar_senha = st.form_submit_button(
            "Guardar nova palavra-passe",
            use_container_width=True
        )

    if guardar_senha:
        if len(nova_senha) < 8:
            st.error(
                "Utiliza uma palavra-passe com pelo menos "
                "8 caracteres."
            )
        elif nova_senha != confirmar_senha:
            st.error("As palavras-passe não coincidem.")
        else:
            try:
                sb.auth.get_user()

                sb.auth.update_user({
                    "password": nova_senha
                })

                sb.auth.sign_out()
                st.session_state.modo_recuperacao = False
                st.session_state.utilizador = None

                st.success(
                    "Palavra-passe alterada. "
                    "Já podes iniciar sessão."
                )
                st.rerun()

            except Exception:
                st.error(
                    "Não foi possível alterar a palavra-passe. "
                    "O link pode ter expirado. Solicita outro."
                )

    st.stop()
if "utilizador" not in st.session_state:
    st.session_state.utilizador = None

if st.session_state.utilizador is None:
    st.subheader("Iniciar sessão")

    with st.form("login"):
        email = st.text_input("E-mail")
        senha = st.text_input(
            "Palavra-passe",
            type="password"
        )
        entrar = st.form_submit_button(
            "Entrar",
            use_container_width=True
        )

    if entrar:
        try:
            resposta = sb.auth.sign_in_with_password({
                "email": email.strip(),
                "password": senha
            })
            st.session_state.utilizador = resposta.user
            st.rerun()
        except Exception:
            st.error(
                "Não foi possível iniciar sessão. "
                "Verifica os dados e tenta novamente."
            )

    st.divider()
    st.subheader("Esqueci-me da palavra-passe")

    with st.form("recuperar_senha"):
        email_recuperacao = st.text_input(
            "E-mail da tua conta"
        )
        recuperar = st.form_submit_button(
            "Enviar link de recuperação",
            use_container_width=True
        )
        
    if recuperar:
        if not email_recuperacao.strip():
            st.error("Introduz o teu e-mail.")
        else:
            try:
                sb.auth.reset_password_for_email(
                    email_recuperacao.strip(),
                    {
                        "redirect_to": "https://an-lise-vendas-grafica-e6f8uiekuwqgjztv2h6hom.streamlit.app/"
                    }
                )
                st.success("Verifica a tua caixa de entrada e a pasta de spam.")
            except Exception as erro:
                st.error("Erro ao recuperar a palavra-passe:")
                st.code(str(erro))
            st.caption(
        except Exception:
            st.error(
                "Não foi possível enviar o e-mail. "
                "Verifica o endereço e tenta novamente."
            )
            )

    st.info(
        "Utiliza uma conta criada em Supabase → "
        "Authentication → Users. A conta também "
        "precisa de estar associada a uma empresa."
    )
    st.stop()

# Confirmar a sessão atual
try:
    utilizador = sb.auth.get_user().user
    if utilizador is None:
        raise Exception("Sessão inválida")
    st.session_state.utilizador = utilizador
except Exception:
    st.session_state.utilizador = None
    st.warning("A sessão expirou. Inicia sessão novamente.")
    st.stop()

user_id = utilizador.id

# Carregar empresas às quais o utilizador pertence
try:
    membros = (
        sb.table("membros_empresa")
        .select("empresa_id,papel")
        .eq("user_id", user_id)
        .eq("ativo", True)
        .execute()
        .data
    )

    if not membros:
        st.error("Esta conta ainda não está associada a uma empresa ativa.")
        st.stop()

    ids_empresas = list({m["empresa_id"] for m in membros})

    empresas = (
        sb.table("empresas")
        .select("id,nome")
        .in_("id", ids_empresas)
        .eq("ativo", True)
        .execute()
        .data
    )

    if not empresas:
        st.error("Não foi encontrada nenhuma empresa ativa acessível.")
        st.stop()

except Exception as erro:
    st.error(f"Não foi possível carregar as empresas: {erro}")
    st.stop()

nomes_empresas = {e["nome"]: e["id"] for e in empresas}

with st.sidebar:
    st.subheader("Conta")
    st.caption(utilizador.email or "Utilizador autenticado")

    empresa_nome = st.selectbox(
        "Empresa",
        list(nomes_empresas.keys())
    )
    empresa_id = nomes_empresas[empresa_nome]

    if st.button("Terminar sessão", use_container_width=True):
        try:
            sb.auth.sign_out()
        finally:
            st.session_state.utilizador = None
            st.rerun()

# Carregar filiais autorizadas
try:
    filiais = (
        sb.table("filiais")
        .select("id,nome,codigo")
        .eq("empresa_id", empresa_id)
        .eq("ativo", True)
        .execute()
        .data
    )
except Exception as erro:
    st.error(f"Não foi possível carregar as filiais: {erro}")
    st.stop()

if not filiais:
    st.warning(
        "Não existe uma filial ativa acessível para esta empresa. "
        "Cria uma filial e atribui-a ao utilizador através das regras administrativas."
    )
    st.stop()

opcoes_filiais = {
    f"{f['nome']} ({f['codigo']})": f["id"]
    for f in filiais
}

with st.sidebar:
    filial_nome = st.selectbox(
        "Filial",
        list(opcoes_filiais.keys())
    )

filial_id = opcoes_filiais[filial_nome]

# Papel do utilizador nesta empresa
papeis = [m["papel"] for m in membros if m["empresa_id"] == empresa_id]
papel = papeis[0] if papeis else ""

st.divider()

pagina = st.radio(
    "Menu",
    [
        "Painel",
        "Clientes",
        "Produtos e serviços",
        "Nova venda",
        "Vendas",
        "Relatórios"
    ],
    horizontal=True
)

# PAINEL
if pagina == "Painel":
    st.header("Painel de controlo")

    try:
        vendas = (
            sb.table("vendas")
            .select("id,numero,estado,criado_em")
            .eq("empresa_id", empresa_id)
            .eq("filial_id", filial_id)
            .execute()
            .data
        )

        df = pd.DataFrame(vendas)

        if df.empty:
            st.info("Ainda não existem vendas registadas nesta filial.")
        else:
            total_vendas = len(df)
            pendentes = int((df["estado"] == "pendente").sum())
            concluidas = int((df["estado"] == "concluida").sum())

            c1, c2, c3 = st.columns(3)
            c1.metric("Número de vendas", total_vendas)
            c2.metric("Pendentes", pendentes)
            c3.metric("Concluídas", concluidas)

            df["criado_em"] = pd.to_datetime(
                df["criado_em"], errors="coerce"
            )
            df["dia"] = df["criado_em"].dt.date

            st.subheader("Vendas por dia")
            por_dia = (
                df.dropna(subset=["dia"])
                .groupby("dia")
                .size()
                .reset_index(name="Quantidade")
            )
            if not por_dia.empty:
                st.line_chart(
                    por_dia.set_index("dia")["Quantidade"]
                )

            st.subheader("Estado das vendas")
            st.bar_chart(df["estado"].value_counts())

    except Exception as erro:
        st.error(f"Erro ao carregar o painel: {erro}")

# CLIENTES
elif pagina == "Clientes":
    st.header("Gestão de clientes")

    with st.form("novo_cliente", clear_on_submit=True):
        nome = st.text_input("Nome do cliente *")
        telefone = st.text_input("Telefone")
        email_cliente = st.text_input("E-mail do cliente")
        endereco = st.text_input("Endereço")
        guardar = st.form_submit_button("Registar cliente")

    if guardar:
        if not nome.strip():
            st.error("O nome do cliente é obrigatório.")
        else:
            try:
                sb.table("clientes").insert({
                    "empresa_id": empresa_id,
                    "nome": nome.strip(),
                    "telefone": telefone.strip() or None,
                    "email": email_cliente.strip() or None,
                    "endereco": endereco.strip() or None,
                    "criado_por": user_id
                }).execute()
                st.success("Cliente registado com sucesso.")
                st.rerun()
            except Exception as erro:
                st.error(f"Não foi possível registar o cliente: {erro}")

    try:
        clientes = (
            sb.table("clientes")
            .select("id,nome,telefone,email,endereco")
            .eq("empresa_id", empresa_id)
            .eq("ativo", True)
            .order("nome")
            .execute()
            .data
        )
        st.subheader("Clientes registados")
        st.dataframe(
            pd.DataFrame(clientes),
            use_container_width=True,
            hide_index=True
        )
    except Exception as erro:
        st.error(f"Erro ao consultar clientes: {erro}")

# PRODUTOS E SERVIÇOS
elif pagina == "Produtos e serviços":
    st.header("Catálogo")

    if papel in ["administrador_empresa", "administrador_sistema"]:
        with st.form("novo_produto", clear_on_submit=True):
            nome_produto = st.text_input("Nome do produto ou serviço *")
            descricao = st.text_input("Descrição")
            categoria = st.selectbox(
                "Categoria",
                ["produto", "servico", "material"]
            )
            preco = st.number_input(
                "Preço base (AOA)",
                min_value=0.0,
                step=100.0
            )
            guardar_produto = st.form_submit_button("Adicionar ao catálogo")

        if guardar_produto:
            if not nome_produto.strip():
                st.error("O nome é obrigatório.")
            else:
                try:
                    sb.table("produtos_servicos").insert({
                        "empresa_id": empresa_id,
                        "nome": nome_produto.strip(),
                        "descricao": descricao.strip() or None,
                        "categoria": categoria,
                        "preco_base": preco
                    }).execute()
                    st.success("Item adicionado ao catálogo.")
                    st.rerun()
                except Exception as erro:
                    st.error(f"Não foi possível guardar: {erro}")
    else:
        st.info("Apenas administradores da empresa podem gerir o catálogo.")

    try:
        catalogo = (
            sb.table("produtos_servicos")
            .select("nome,descricao,categoria,preco_base,ativo")
            .eq("empresa_id", empresa_id)
            .eq("ativo", True)
            .order("nome")
            .execute()
            .data
        )
        st.dataframe(
            pd.DataFrame(catalogo),
            use_container_width=True,
            hide_index=True
        )
    except Exception as erro:
        st.error(f"Erro ao consultar o catálogo: {erro}")

# NOVA VENDA
elif pagina == "Nova venda":
    st.header("Registar venda")

    try:
        clientes = (
            sb.table("clientes")
            .select("id,nome")
            .eq("empresa_id", empresa_id)
            .eq("ativo", True)
            .order("nome")
            .execute()
            .data
        )

        opcoes_clientes = {"Sem cliente associado": None}
        opcoes_clientes.update({c["nome"]: c["id"] for c in clientes})

        with st.form("registar_venda", clear_on_submit=True):
            cliente_nome = st.selectbox(
                "Cliente",
                list(opcoes_clientes.keys())
            )
            descricao_item = st.text_input("Descrição do item vendido *")
            quantidade = st.number_input(
                "Quantidade", min_value=0.01, value=1.0, step=1.0
            )
            preco_unitario = st.number_input(
                "Preço unitário (AOA)",
                min_value=0.0,
                step=100.0
            )
            desconto = st.number_input(
                "Desconto total do item (AOA)",
                min_value=0.0,
                step=100.0
            )
            observacoes = st.text_area("Observações")
            confirmar = st.form_submit_button("Registar venda")

        if confirmar:
            if not descricao_item.strip():
                st.error("A descrição do item é obrigatória.")
            elif desconto > quantidade * preco_unitario:
                st.error("O desconto não pode ultrapassar o valor do item.")
            else:
                try:
                    resultado = sb.rpc("criar_venda", {
                        "p_empresa_id": empresa_id,
                        "p_filial_id": filial_id,
                        "p_cliente_id": opcoes_clientes[cliente_nome],
                        "p_descricao": descricao_item.strip(),
                        "p_quantidade": quantidade,
                        "p_preco_unitario": preco_unitario,
                        "p_desconto": desconto,
                        "p_observacoes": observacoes.strip() or None
                    }).execute()

                    st.success(
                        "Venda registada com sucesso. "
                        f"Referência interna: {resultado.data}"
                    )
                except Exception as erro:
                    st.error(f"Não foi possível registar a venda: {erro}")

    except Exception as erro:
        st.error(f"Erro ao preparar o formulário: {erro}")

# CONSULTA DE VENDAS
elif pagina == "Vendas":
    st.header("Consulta de vendas")

    try:
        vendas = (
            sb.table("vendas")
            .select(
                "id,numero,estado,moeda,criado_em,observacoes,"
                "itens_venda(descricao,quantidade,preco_unitario,desconto)"
            )
            .eq("empresa_id", empresa_id)
            .eq("filial_id", filial_id)
            .order("criado_em", desc=True)
            .execute()
            .data
        )

        linhas = []
        for venda in vendas:
            total = sum(
                float(item["quantidade"]) * float(item["preco_unitario"])
                - float(item["desconto"])
                for item in (venda.get("itens_venda") or [])
            )
            linhas.append({
                "Número": venda["numero"],
                "Estado": venda["estado"],
                "Data": venda["criado_em"],
                "Total (AOA)": total,
                "Observações": venda.get("observacoes")
            })

        st.dataframe(
            pd.DataFrame(linhas),
            use_container_width=True,
            hide_index=True
        )
    except Exception as erro:
        st.error(
            "Não foi possível consultar as vendas. "
            "Confirma as permissões de leitura das vendas e dos itens. "
            f"Detalhe: {erro}"
        )

# RELATÓRIOS
elif pagina == "Relatórios":
    st.header("Relatórios")

    try:
        vendas = (
            sb.table("vendas")
            .select("id,numero,estado,criado_em")
            .eq("empresa_id", empresa_id)
            .eq("filial_id", filial_id)
            .execute()
            .data
        )

        df = pd.DataFrame(vendas)

        if df.empty:
            st.info("Não há dados suficientes para gerar relatórios.")
        else:
            st.metric("Vendas registadas", len(df))
            st.subheader("Distribuição por estado")
            st.dataframe(
                df["estado"].value_counts().rename_axis("Estado")
                .reset_index(name="Quantidade"),
                use_container_width=True,
                hide_index=True
            )

            csv = df.to_csv(index=False).encode("utf-8-sig")
            st.download_button(
                "Descarregar relatório CSV",
                data=csv,
                file_name="relatorio_vendas.csv",
                mime="text/csv"
            )
    except Exception as erro:
        st.error(f"Não foi possível gerar o relatório: {erro}")

st.divider()
st.caption("Sistema de Gestão e Análise de Vendas — versão inicial integrada")
