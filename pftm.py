#!/usr/bin/python3
import os, sys, json

fn = 'map_2.log'
channel_filter = 'SRG-C'
if not os.path.isfile(fn):
  exit(1)

objects = {}

class Map:
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
    #print('<<<<< >>>>> del connection:', dt, character['name'], objct['objId'])
    if path_base == '/api/rest/System':
      pass #print('<<<<< >>>>> del systems:', ",".join(path_ids))

  def deleted_system(self, system_id, dt, character, objct, path_base, path_ids):
    #print(path_base, '' if not path_ids else ",".join(path_ids))
    if path_base == '/api/rest/System':
      assert len(path_ids) >= 1
      assert str(objct['objId']) in path_ids
      assert system_id == "'"+objct['objName']+"'"
    else:
      assert path_base == ''
    #print('<<<<< >>>>> del system:', dt, character['name'], objct['objId'], objct['objName'])
    if len(path_ids) > 1:
      pass #print('<<<<< >>>>> del systems:', ",".join(path_ids))

  def deleted_signature(self, signature_id, dt, character, objct, path_base, path_ids):
    #print(path_base, '' if not path_ids else ",".join(path_ids))
    if path_base == '/api/rest/Signature':
      if path_ids:
        assert str(objct['objId']) in path_ids
    else:
      assert path_base == ''
    #print('<<<<< >>>>> del signature:', dt, character['name'], objct['objId'], objct['objName'])
    if len(path_ids) > 1:
      pass #print('<<<<< >>>>> del signatures:', ",".join(path_ids))

  def updated_connection(self, connection_id, dt, character, objct, main, path_base, path_ids):
    pass

  def updated_system(self, system_id, dt, character, objct, main, path_base, path_ids):
    pass

  def updated_signature(self, signature_id, dt, character, objct, main, path_base, path_ids):
    pass

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
    #print('<<<<< >>>>> add connection:', dt, character['name'], objct['objId'], source, target)

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
    #print('<<<<< >>>>> add system:', dt, character['name'], objct['objId'], objct['objName'], locked, statusId)

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
    #assert main['description'].get('new') == 'Разрушенный научный аванпост Gurista (Ruined Guristas Science Outpost)'
    #print('<<<<< >>>>> add signature:', dt, character['name'], objct['objId'], objct['objName'])

map = Map()
with open(fn) as f:
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
    dt = obj.get('datetime')
    extra = obj.get('extra')
    path = extra.get('path')
    thumb = extra.get('thumb')
    url = thumb.get('url')
    object_id, object_name = objct.get('objId'), objct.get('objName')
    if channel.get('channelName') != channel_filter: continue
    #if character_name != 'Qunibbra Do': continue

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

    kuk = False
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
          kuk = True
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
    if kuk:
      if obj: print(obj, "\n")
      print(
          dt,
          '|', message_type, message_parts[1],
          '|', character_name,
          '|', object_id, object_name,
          '|', path_base, path_ids,
          "\n", formatted)
      print("---------------------")

exit(0)
