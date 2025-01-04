#!python3

import xml.etree.ElementTree as ET
import pandoc
import plumbum
import requests
import os
import time
import functools

if False:
    import logging
    import http.client as http_client

    http_client.HTTPConnection.debuglevel = 1

    logging.basicConfig()
    logging.getLogger().setLevel(logging.DEBUG)
    requests_log = logging.getLogger("requests.packages.urllib3")
    requests_log.setLevel(logging.DEBUG)
    requests_log.propagate = True

ns = {
    'mediawiki': 'http://www.mediawiki.org/xml/export-0.10/'
}

API_KEY = 'gera isso aqui no painel de admin do discourse!'

@functools.lru_cache
def upload_image(name, data):
    local = os.path.join('images', name)
    with open(local, 'wb') as f:
        f.write(data)

    r = requests.post('https://discourse.lhc.net.br/uploads.json',
      files = {
        'files[]': (name, open(local, 'rb'), 'image/jpeg'),
      },
      data = {
        'type': 'image',
        'synchronous': True,
      },
      headers = {
        'Api-Key': API_KEY,
        'Api-Username': 'system',
      }
    )

    if r.status_code != 200:
      if 'rate_limit' in str(r.content):
        print('Esperando o servidor liberar')
        time.sleep(20)
        return upload_image(name, data)

    return r.json()['short_url']

@functools.lru_cache
def fetch_image(name):
    url = f'https://lhc.net.br/w/index.php?title=Especial:Redirecionar/file&wpvalue={nome}'
    r = requests.get(url)
    if r.status_code != 200:
        print(f'Nao consegui pegar a imagem {nome}, {r} (ou não era imagem :P)')
        return None

    print(f'Obti imagem do Wiki, fazendo upload no Discourse: {nome}')
    short_url = upload_image(nome, r.content)
    print(f'   ... feito upload para {short_url}')

    return short_url

def convert_to_html(wikitext):
    pd = pandoc.read(source=wikitext, format='mediawiki')

    for elt in pandoc.iter(pd):
        if isinstance(elt, (pandoc.types.Link, pandoc.types.Image)):
            nome = elt[2][0]

            if short_url := fetch_image(nome):
                elt.__class__ = pandoc.types.Image                
                elt[2] = (short_url, elt[2][1])

    return pandoc.write(pd, format='html')

def pages(root):
    for child in root.findall('mediawiki:page', ns):
        revision = child.find('mediawiki:revision', ns)
        if revision is None:
            continue

        title = child.find('mediawiki:title', ns)
        model = revision.find('mediawiki:model', ns)
        format = revision.find('mediawiki:format', ns)
        text = revision.find('mediawiki:text', ns)

        if model.text != 'wikitext':
            print(f"Pagina '{title.text}' tem modelo não esperado ({model.text})")
            continue
        if format.text != 'text/x-wiki':
            print(f"Pagina '{title.text}' tem formato não esperado ({format.text})")
            continue
        if text.text is None:
            print(f"Pagina '{title.text}' tem texto nulo, ignorando")
            continue
        if text.text.startswith(('#REDIRECT ', '#REDIRECIONAMENTO ')):
            print(f"Pagina '{title.text}' é só redirecionamento, ignorando")
            continue

        # padrao do discourse: se len(title.text) < 15, nao cria topico!
        # configuracoa pra mudar temporariamente: min topic title length

        print(f"Convertendo pagina '{title.text}'...")
        try:
            text = convert_to_html(text.text)
        except plumbum.commands.processes.ProcessExecutionError as a:
            print(f"Pagina {title.text} falhou a conversão, modifique o XML para passar: {a}")
            continue
            
        yield (title.text, text)

def create_page(title, html):
    print(f"Criando tópico '{title}' na categoria wiki antigo")
    r = requests.post('https://discourse.lhc.net.br/posts.json',
        json = {
            'title': title,
            'raw': html,
            'category': 29,
        },
        headers = {
            'Api-Key': API_KEY,
            'Api-Username': 'system',
        }
    )
    if r.status_code != 200:
      if 'rate_limit' in str(r.content):
        print('Esperando o servidor liberar')
        time.sleep(20)
        return create_page(title, html)
  
    elif r.status_code == 422:
      print(r)

    else:
      r.raise_for_status()

if __name__ == '__main__':
    tree = ET.parse('LHC-20241127010745.xml')
    root = tree.getroot()

    for title, html in pages(root):
        create_page(title, html)
