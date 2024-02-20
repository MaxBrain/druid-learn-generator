```
generate.py -d : debug and info output
generate.py --debug : debug and info output

generate.py -v : only info output
generate.py --verbose : only info output
```

- Скрипт проходит по папке `druid/example/examples` и ищет файлы `.gui` и `.gui_script`
- Скрипт создаёт файлы с описанием создания GUI или заменяет их если в тексте нет строки `#generated`
