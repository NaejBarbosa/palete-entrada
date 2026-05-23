# 🍱 Controle de Entrada de Paletes - Câmaras Frias

Aplicativo web responsivo para registrar paletes armazenados em câmaras frias.  
Desenvolvido com **Streamlit**, os dados são salvos em uma planilha pública do Google Sheets e o sistema pode ser usado diretamente pelo navegador do seu Android.

👉 [Acessar a planilha de dados](https://docs.google.com/spreadsheets/d/1HoN-VLyO5y9wJ4NKdpz42-BljRzT4VeJVY-Wio4CO6g/edit?usp=drivesdk)

---

## ✨ Funcionalidades

- Seleção de **câmara** (Resfriados 1/2, Congelados 1/2) e **vaga** (lista pré-definida com 80 opções)
- ✅ **Validação em tempo real**: impede que a mesma combinação câmara+vaga seja usada mais de uma vez
- ➕ **Múltiplos produtos por palete** – cada produto gera uma linha na planilha
- 📅 Validação de **validade** no formato `dd/mm/aaaa` (data real)
- 🔁 Confirmação antes do envio: pergunta se deseja adicionar mais produtos para o mesmo palete
- 📱 Layout responsivo (funciona perfeitamente no celular Android)
- ☁️ Deploy gratuito no **Streamlit Cloud**

---

## 📦 Pré‑requisitos

- Conta [GitHub](https://github.com)
- Planilha Google Sheets **pública com permissão de edição** (já configurada no link acima)
- [Conta de serviço do Google](https://console.cloud.google.com/) com acesso à API Google Sheets
- Arquivo `.json` com as credenciais da conta de serviço

---

## 🛠️ Configuração local (opcional)

1. **Clone o repositório**
   ```bash
   git clone https://github.com/seu-usuario/palete-entrada.git
   cd palete-entrada
