#!/usr/bin/python3

""" Q.Pathfinder Time Machine

Prerequisites:
    * Have a Python 3 environment available to you (possibly by using a
      virtual environment: https://virtualenv.pypa.io/en/stable/).
    * Run pip install -r requirements.txt with this directory as your root.

To run this example, make sure you have completed the prerequisites and then
run the following command from this directory:

$ chcp 65001 & @rem on Windows only!
$ python pftm.py --map=filename.log
"""
import os
import sys
import json
import typing
import datetime

import console_app
from __init__ import __version__

objects = {}
g_debug_printf: typing.Optional[bool] = None
g_channel_filter: typing.Optional[str] = None

class PfSystem:
  def __init__(self, id: int, nm: str, at: datetime.datetime):
    self.id: int = id
    self.nm: str = nm
    self.at: datetime.datetime = at
    self.last: datetime.datetime = at
    self.locked: typing.Optional[bool] = None
    self.statusId: typing.Optional[bool] = None

class PfConnection:
  def __init__(self, id: int, source: int, target: int, at: datetime.datetime):
    self.id: int = id
    self.source: int = source
    self.target: int = target

class PfStorage:
  def __init__(self):
    self.systems: typing.Dict[int, PfSystem] = {}
    self.connections: typing.Dict[int, PfConnection] = {}

  def get_system(self, id: int) -> typing.Optional[PfSystem]:
    s: typing.Optional[PfSystem] = self.systems.get(int(id), None)
    return s

  def add_system(self, id: int, nm: str, at: datetime.datetime) -> PfSystem:
    _id: int = int(id)
    assert self.systems.get(_id) is None
    # название системы должно быть указано
    assert nm is not None
    # на самом деле на карте может существовать несколько систем с одинаковым названием и разными id
    # судя по всему это происходит тогда, на карту наносится вручную? уже существующая там система
    # у таких систем будут разные id, но одинаковое название (например лоусек)
    self.systems[_id] = PfSystem(_id, nm, at)
    return self.systems.get(_id)

  def del_system(self, id: int, dt: datetime.datetime):
    _id: int = int(id)
    # если лог пишется не с самого начала (это нормально), то тут может быть выполнена попытка удалить то, чего нет
    s: typing.Optional[PfSystem] = self.get_system(_id)
    if s is None:
      if g_debug_printf:
        print('FAIL: unable to delete system {} at {} (ignored)'.format(_id, dt))
      return
    else:
      s.last = dt
    del self.systems[_id]

  def upd_system(self, id: int, nm: str, dt: datetime.datetime) -> PfSystem:
    _id: int = int(id)
    # если лог пишется не с самого начала (это нормально), то тут системы может не быть (создаём?)
    s: typing.Optional[PfSystem] = self.get_system(_id)
    if s is None:
      if g_debug_printf:
        print('FAIL: system {} not exists on update at {} (recreated)'.format(_id, dt))
      s = self.add_system(_id, nm, dt)
    s.last = dt
    return s

  def get_connection(self, id: int) -> typing.Optional[PfConnection]:
    c: typing.Optional[PfConnection] = self.connections.get(int(id), None)
    return c

  def add_connection(self, id: int, src: int, tgt: int, at: datetime.datetime) -> PfConnection:
    _id: int = int(id)
    _src: int = int(src)
    _tgt: int = int(tgt)
    assert self.connections.get(_id) is None
    self.connections[_id] = PfConnection(_id, _src, _tgt, at)
    return self.connections.get(_id)

  def del_connection(self, id: int, dt: datetime.datetime):
    _id: int = int(id)
    # если лог пишется не с самого начала (это нормально), то тут может быть выполнена попытка удалить то, чего нет
    c: typing.Optional[PfConnection] = self.get_connection(_id)
    # в том числе браузер отправляет несколько запросов на удаление одних и тех же систем (удаляется одна, которая
    # тянет за собой группу других, и тут приходит запрос на удаление той системы, что была в группе, и снова удаляется
    # вся группа)
    if c is None:
      if g_debug_printf:
        print('FAIL: unable to delete connection {} at {} (ignored)'.format(_id, dt))
      return
    else:
      c.last = dt
    del self.connections[_id]


class PfMap:
  def __init__(self):
    self.storage: PfStorage = PfStorage()

  def convert_items(self, data: typing.Optional[str]):
    if not data:
      return None
    if '[' in data:
      return json.loads(data)  # ["bubble"]
    else:
      return [data]  # stargate

  def deleted_connection(self, connection_id, dt, character, objct, path_base, path_ids):
    #print(path_base, '' if not path_ids else ",".join(path_ids))
    assert connection_id == "'wh'"
    assert objct['objName'] == 'wh'
    if path_base == '/api/rest/Connection':
      assert len(path_ids) == 1
      assert int(path_ids[0]) == int(objct['objId'])
    elif path_base == '/cron/deleteEolConnections': pass
    elif path_base == '/cron/deleteExpiredConnections': pass
    elif path_base == '/api/rest/System':
      assert len(path_ids) >= 1
    else:
      assert path_base == ''
    if g_debug_printf:
      print('<<<<< >>>>> del connection:', dt, character['name'], objct['objId'])
    self.storage.del_connection(objct['objId'], dt)
    if path_base == '/api/rest/System':
      if g_debug_printf:
        print('<<<<< >>>>> del connections:', dt, ",".join(path_ids))

  def deleted_system(self, system_id, dt, character, objct, path_base, path_ids):
    #print(path_base, '' if not path_ids else ",".join(path_ids))
    if path_base == '/api/rest/System':
      assert len(path_ids) >= 1
      assert str(objct['objId']) in path_ids
      assert system_id == "'"+objct['objName']+"'"
    else:
      assert path_base == ''
    if g_debug_printf:
      print('<<<<< >>>>> del system:', dt, character['name'], objct['objId'], objct['objName'])
    self.storage.del_system(objct['objId'], dt)
    if len(path_ids) > 1:
      if g_debug_printf:
        print('<<<<< >>>>> del systems:', dt, ",".join(path_ids))
      for id in path_ids:
        if int(id) != int(objct['objId']):
          self.storage.del_system(id, dt)

  def deleted_signature(self, signature_id, dt, character, objct, path_base, path_ids):
    #print(path_base, '' if not path_ids else ",".join(path_ids))
    if path_base == '/api/rest/Signature':
      if path_ids:
        assert str(objct['objId']) in path_ids
    else:
      assert path_base == ''
    if g_debug_printf:
      print('<<<<< >>>>> del signature:', dt, character['name'], objct['objId'], objct['objName'])
    if len(path_ids) > 1:
      if g_debug_printf:
        print('<<<<< >>>>> del signatures:', dt, ",".join(path_ids))

  def updated_connection(self, connection_id, dt, character, objct, main, path_base, path_ids):
    #print(path_base, '' if not path_ids else ",".join(path_ids), main)
    assert connection_id in ["'wh'","'stargate'"]
    assert objct['objName'] in ['wh','stargate']
    if path_base == '/api/Map/updateUserData':
      assert not path_ids
    elif path_base == '/api/rest/Connection':
      assert not path_ids
    elif path_base == '/api/Map/updateData':
      assert not path_ids
    elif path_base == '/api/Map/updateUnloadData':
      assert not path_ids
    else:
      assert path_base == ''
    if main.get('source'):
      assert main['source'].get('new') is not None
    if main.get('target'):
      assert main['target'].get('new') is not None
    if 'scope' in main:
      assert main['scope']['new'] in ['wh','stargate']
    assert len(set(main.keys()) - set(['source','target','type','scope','sourceEndpointType','targetEndpointType'])) == 0
    source: int = main['source'].get('new') if 'source' in main else None
    target: int = main['target'].get('new') if 'target' in main else None
    typ = self.convert_items(main['type'].get('new')) if 'type' in main else None  # '["wh_fresh","wh_jump_mass_l"]'
    scope: str = main['scope'].get('new') if 'scope' in main else None  # 'stargate'
    sourceEndpointType = self.convert_items(main['sourceEndpointType'].get('new')) if 'sourceEndpointType' in main else None  # '["bubble"]'
    targetEndpointType = self.convert_items(main['targetEndpointType'].get('new')) if 'targetEndpointType' in main else None  # '["bubble"]'
    if g_debug_printf:
      print('<<<<< >>>>> upd connection:', dt, character['name'], objct['objId'], source, target, typ, scope, sourceEndpointType)

  def updated_system(self, system_id, dt, character, objct, main, path_base, path_ids):
    #print(path_base, '' if not path_ids else ",".join(path_ids), main)
    if path_base == '/api/Map/updateUserData':
      assert not path_ids
    elif path_base == '/api/Map/updateData':
      assert not path_ids
    elif path_base == '/api/rest/System':
      if path_ids:
        assert len(path_ids) == 1
        assert str(objct['objId']) in path_ids
    else:
      assert path_base == ''
    assert len(set(main.keys()) - set(['active','locked','statusId','description','alias','rallyPoke'])) == 0
    active = main.get('active')
    locked: bool = True if 'locked' in main and main['locked']['new'] == 1 else None
    statusId: bool = main['statusId'].get('new') if 'statusId' in main else None
    description: str = main['description'].get('new') if 'description' in main else None
    alias: str = main['alias'].get('new') if 'alias' in main else None
    rallyPoke: int = main['rallyPoke'].get('new') if 'rallyPoke' in main else None
    if g_debug_printf:
      print('<<<<< >>>>> upd system:', dt, character['name'], objct['objId'], objct['objName'], locked, statusId, description, alias, rallyPoke)
    if active:
      # каким-то образом системы "архивируются?" и не пересоздаются, а переходят из not active в active состояние
      # это признак того, что они "существуют", поэтому мы должны создать такую систему и держать до её удаления
      if self.storage.get_system(objct['objId']) is None:
        self.storage.add_system(objct['objId'], objct['objName'], dt)
    s: PfSystem = self.storage.upd_system(objct['objId'], objct['objName'], dt)
    if locked is not None:
      s.locked = locked
    if statusId is not None:
      s.statusId = statusId

  def updated_signature(self, signature_id, dt, character, objct, main, path_base, path_ids):
    #print(path_base, '' if not path_ids else ",".join(path_ids), main)
    if path_base == '/api/rest/Signature':
      if path_ids:
        assert len(path_ids) == 1
        assert str(objct['objId']) in path_ids
    else:
      assert path_base == ''
    assert len(set(main.keys()) - set(['groupId','typeId','name','description','connectionId'])) == 0
    groupId: int = main['groupId'].get('new') if 'groupId' in main else None
    typeId: int = main['typeId'].get('new') if 'typeId' in main else None
    name: int = main['name'].get('new') if 'name' in main else None
    description: int = main['description'].get('new') if 'description' in main else None
    connectionId: int = main['connectionId'].get('new') if 'connectionId' in main else None
    if g_debug_printf:
      print('<<<<< >>>>> upd signature:', dt, character['name'], objct['objId'], objct['objName'], groupId, typeId, name, description, connectionId)

  def created_connection(self, connection_id, dt, character, objct, main, path_base, path_ids):
    #print(path_base, '' if not path_ids else ",".join(path_ids), main)
    assert connection_id in ["'wh'","'stargate'"]
    assert objct['objName'] in ['wh','stargate']
    if path_base == '/api/Map/updateUserData': pass
    elif path_base == '/api/rest/Connection':
      assert len(path_ids) == 0
    else:
      assert path_base == ''
    assert main.get('source')
    assert main['source'].get('old') is None
    assert main.get('target')
    assert main['target'].get('old') is None
    assert len(set(main.keys()) - set(['source','target','scope','type'])) == 0
    source = main['source']['new']
    target = main['target']['new']
    if 'scope' in main:
      assert main['scope']['new'] in ['wh','stargate']
    if 'type' in main:
      assert main['type']['new'] in ['["wh_fresh"]','["stargate"]']
    typ = self.convert_items(main['type'].get('new')) if 'type' in main else None  # '["wh_fresh","stargate"]'
    scope: str = main['scope'].get('new') if 'scope' in main else None  # 'stargate'
    if g_debug_printf:
      print('<<<<< >>>>> add connection:', dt, character['name'], objct['objId'], source, target, typ, scope)
    c: PfConnection = self.storage.add_connection(objct['objId'], source, target, dt)

  def created_system(self, system_id, dt, character, objct, main, path_base, path_ids):
    #print(path_base, '' if not path_ids else ",".join(path_ids), main)
    if path_base == '/api/Map/updateUserData':
      assert not path_ids
    elif path_base == '/api/rest/System':
      assert not path_ids
    else:
      assert path_base == ''
    assert main.get('active')
    assert main['active'].get('old') is None
    assert main['active'].get('new') == 1
    assert len(set(main.keys()) - set(['active','locked','statusId'])) == 0
    locked: bool = True if 'locked' in main and main['locked']['new'] == 1 else None
    statusId: bool = main['statusId'].get('new') if 'statusId' in main else None
    if g_debug_printf:
      print('<<<<< >>>>> add system:', dt, character['name'], objct['objId'], objct['objName'], locked, statusId)
    s: PfSystem = self.storage.add_system(objct['objId'], objct['objName'], dt)
    if locked is not None:
      s.locked = locked
    if statusId is not None:
      s.statusId = statusId

  def created_signature(self, signature_id, dt, character, objct, main, path_base, path_ids):
    #print(path_base, '' if not path_ids else ",".join(path_ids), main)
    if path_base == '/api/rest/Signature':
      assert not path_ids
    else:
      assert path_base == ''
    assert len(set(main.keys()) - set(['groupId','typeId','name','description'])) == 0
    assert main.get('groupId')
    assert main['groupId'].get('old') is None
    assert main.get('typeId')
    assert main['typeId'].get('old') is None
    assert main.get('name')
    assert main['name'].get('old') is None
    assert main['name'].get('new') == objct['objName']
    assert main.get('description')
    assert main['description'].get('old') is None
    groupId: int = main['groupId'].get('new') if 'groupId' in main else None
    typeId: int = main['typeId'].get('new') if 'typeId' in main else None
    name: int = main['name'].get('new') if 'name' in main else None
    description: int = main['description'].get('new') if 'description' in main else None
    #assert main['description'].get('new') == 'Разрушенный научный аванпост Gurista (Ruined Guristas Science Outpost)'
    if g_debug_printf:
      print('<<<<< >>>>> add signature:', dt, character['name'], objct['objId'], objct['objName'], groupId, typeId, name, description)

def main():
  global g_debug_printf
  global g_channel_filter

  g_channel_filter = 'SRG-C'  #TODO

  # работа с параметрами командной строки, получение настроек запуска программы
  argv_prms = console_app.get_argv_prms()
  g_debug_printf = argv_prms['verbose_mode']

  if not os.path.isfile(argv_prms['map']):
    exit(1)

  map = PfMap()
  with open(argv_prms['map']) as f:
    for line in f:
      obj = json.loads(line)
      message = obj.get('message')
      message_parts = message.split(' ', 1)
      message_type = message_parts[0]
      message_id = message_parts[1]
      context = obj.get('context')
      data = context.get('data')
      main = data.get('main')
      objct = data.get('object')
      character = data.get('character')
      character_name = character.get('name')
      channel = data.get('channel')
      formatted = data.get('formatted')
      dt = datetime.datetime.strptime(obj.get('datetime'),"%Y-%m-%dT%H:%M:%S.%f+00:00")  # "2023-10-27T07:38:33.856015+00:00"
      dt = dt.replace(microsecond=0)
      extra = obj.get('extra')
      path = extra.get('path')
      thumb = extra.get('thumb')
      url = thumb.get('url')
      object_id, object_name = objct.get('objId'), objct.get('objName')
      if g_channel_filter:
        if channel.get('channelName') != g_channel_filter: continue
      #debug:if character_name != 'Qunibbra Do': continue

      if message_type == 'map':
        continue
      elif message_type == 'system' or message_type == 'signature' or message_type == 'connection':
        pass
      else:
        print('Unknown message_type:', obj)
        exit(1)

      path_base = None
      path_ids = None
      if path == '/cron/deleteEolConnections' or \
         path == '/cron/deleteExpiredConnections' or \
         path == '/api/Map/updateData' or \
         path == '/api/Map/updateUserData' or \
         path == '/api/Map/updateUnloadData':
        path_base = path
      elif path.startswith('/api/rest/Connection'):  # номер соединения, м.б. пустой строкой
        path_base = '/api/rest/Connection'
        path_ids = path[len(path_base)+1:]
        path_ids = [] if not path_ids else path_ids.split(',')
      elif path.startswith('/api/rest/System'):  # номера систем, м.б. пустым списком
        path_base = '/api/rest/System'
        path_ids = path[len(path_base)+1:]
        path_ids = [] if not path_ids else path_ids.split(',')
      elif path.startswith('/api/rest/Signature'):  # номера сигнатур, м.б. пустым списком
        path_base = '/api/rest/Signature'
        path_ids = path[len(path_base)+1:]
        path_ids = [] if not path_ids else path_ids.split(',')
      elif path.startswith('/api/rest/Map/'):  # создание карты
        continue
      else:
        print('Unknown extra.path:', obj)
        assert False

      if objects.get(str(object_id)):
        if object_name != objects.get(str(object_id)):
          pass # print("!!!!!!!!!!!!!", objct, objects.get(str(object_id)), line)
      else:
        objects.update({str(object_id): object_name})

      # установка этой переменной приведёт к выводу информации
      # по разбору данных в текущей строке
      debug_this_line = False

      if not main or main.get('active') and main['active']['old'] and not main['active']['new']:
        if not formatted.startswith("Deleted "+message_type):
          print('Unknown deletion:', obj)
          assert False
        if message_type == 'connection':
          map.deleted_connection(message_id, dt, character, objct, path_base, path_ids)
        elif message_type == 'system':
          map.deleted_system(message_id, dt, character, objct, path_base, path_ids)
        elif message_type == 'signature':
          map.deleted_signature(message_id, dt, character, objct, path_base, path_ids)
      else:
        # определяем тип воздействия update-or-create
        updation: bool = False
        for key in main.keys():
          # перехватываем те события, которые прямо свидетельствуют, что объект уже есть
          if message_type == 'signature':
            if key in ['connectionId']:
              updation = True
              break
          elif message_type == 'system':
            if key in ['description']:
              updation = True
              break
          elif message_type == 'connection':
            if key in ['sourceEndpointType','targetEndpointType']:
              updation = True
              break
          if main[key]['old'] is not None:
            updation = True
            break;
        if updation:
          if not formatted.startswith("Updated "+message_type):
            print('Unknown updation:', obj)
            assert False
          if message_type == 'connection':
            map.updated_connection(message_id, dt, character, objct, main, path_base, path_ids)
          elif message_type == 'system':
            map.updated_system(message_id, dt, character, objct, main, path_base, path_ids)
          elif message_type == 'signature':
            map.updated_signature(message_id, dt, character, objct, main, path_base, path_ids)
        else:
          if not formatted.startswith("Created "+message_type):
            print('Unknown creation:', obj)
            assert False
          if message_type == 'connection':
            map.created_connection(message_id, dt, character, objct, main, path_base, path_ids)
          elif message_type == 'system':
            map.created_system(message_id, dt, character, objct, main, path_base, path_ids)
          elif message_type == 'signature':
            map.created_signature(message_id, dt, character, objct, main, path_base, path_ids)

      if debug_this_line:
        # удаляем обработанные тэги, чтобы было видно что именно ещё осталось необработанным?
        del obj['message']
        del obj['context']['data']['character']
        del obj['context']['data']['channel']
        del obj['context']['data']['object']
        del obj['context']['data']['formatted']
        del obj['context']['tag']
        del obj['datetime']
        del obj['level']
        del obj['level_name']
        del obj['channel']
        del obj['extra']['path']
        del obj['extra']['ip']
        del obj['extra']['thumb']
        if not obj['extra']: del obj['extra']
        if not obj['context']['data']['main']: del obj['context']['data']['main']
        if not obj['context']['data']: del obj['context']['data']
        if not obj['context']: del obj['context']
        if obj:
          print(obj, "\n")
        print(
            dt,
            '|', message_type, message_parts[1],
            '|', character_name,
            '|', object_id, object_name,
            '|', path_base, path_ids,
            "\n", formatted)
        print("---------------------")

if __name__ == "__main__":
  main()
  exit(0)
else:
  exit(1)
