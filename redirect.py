#!python3

import requests
import os

def topics():
  page = 0
  while True:
    print(f'Listando tópicos da página {page}...')

    r = requests.get(f'https://discourse.lhc.net.br/c/wiki-antigo/29.json?page={page}')
    if r.status_code != 200:
      r.raise_for_status()
    
    j = r.json()
    if not j['topic_list']['topics']:
      break

    page += 1

    for topic in j['topic_list']['topics']:
      yield topic['id'], topic['title']

def mk_js_redir(id, title):
  return f'''if (title === '{title}') return 'https://discourse.lhc.net.br/t/{id}';'''

def mk_manual_redir(id, title):
  return f'''<li><a href="https://discourse.lhc.net.br/t/{id}">{title}</a></li>'''

if __name__ == '__main__':
  auto_redir_js = []
  manual_redir = []

  for id, title in topics():
    print(f'Criando redirecionamento para página do Wiki: {title}')
    try:
      os.makedirs(f'redirect/{title}', 0o755)
    except FileExistsError:
      pass

    auto_redir_js.append(mk_js_redir(id, title))
    manual_redir.append(mk_manual_redir(id, title))

    with open(f'redirect/{title}/index.html', 'w') as f:
      f.write(f'''<html>
<h1>Redirecionamento automático</h1>
<script>
document.top.href = 'https://discourse.lhc.net.br/t/{id}';
</script>
<meta charset="UTF-8">
<meta http-equiv="refresh" content="0; url=https://discourse.lhc.net.br/t/{id}">
<a href="https://discourse.lhc.net.br/t/{id}">Prosseguir para {title} no Discourse manualmente</a>
''')

  auto_redir_js = '\n  '.join(auto_redir_js)
  manual_redir = '\n'.join(manual_redir)
  with open(f'redirect/index.html', 'w') as f:
    f.write(f'''<html>
<h1>Redirecionamento automático</h1>
<script>

function get_url_to_redir() {{
  const urlParams = new URLSearchParams(window.location.search);
  const title = urlParams.get('title');
  {auto_redir_js}
  return '/index.html';
}}

document.top.href = get_url_to_redir();
</script>
<meta charset="UTF-8">
<noscript>
Sem JavaScript não conseguimos fazer o redirecionamento automático. Escolha a página do Wiki para redirecionar manualmente:
<ul>
{manual_redir}
</ul>
</noscript>
''')
  