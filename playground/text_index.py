from ggbot.utils import benchmark
from ggbot.text.legacy.index import *
from ggbot.steam import *


def test():
    import json

    with benchmark('loading'):
        with open('../.cache/GetAppList.v2.json', 'r', encoding='utf-8') as fp:
            apps = json.load(fp)['applist']['apps']

    with benchmark('indexing'):
        index = Index()
        for app in apps:
            if app['appid'] < 10:
                print(app)
            #print(app['name'])
            index.add(app['name'], app)

    with benchmark('searching'):
        #index.search(ru_to_lat('фэнтэзи граундс'))
        index.search('counter strike')


if __name__ == '__main__':
    test()
