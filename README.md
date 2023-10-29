# Q.Pathfinder Time Machine

Утилита для создания мультфильма (видеоролика) с историей ползания по вормхолам в игре EVE Online. Для создания ролика необходим log-файл, который в фоне сохраняет pathfinder.

## Использование

```bash
mkdir ~/q.pftm
cd ~/q.pftm
git clone git@github.com:Qandra-Si/q.pftm.git ./

wget http://<адрес-вашего-сервера>/history/map/map_2.log
./pftm.py --map=map_2.log
```
