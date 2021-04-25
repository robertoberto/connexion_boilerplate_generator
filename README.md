# Connextion Boilerplate Generator 

Generates python API boilerplate code from openapi 3.0 JSON to [Connextion framework](https://github.com/zalando/connexion)
You can convert openapi YAML to JSON with any utilitary.


You can use virtualenv or directly install pip dependencies:
```
pip install -r requirements.txt
```

To run, just edit cli.py.

Automatic Routing works creating operationId on path/methods with restyresolver prefix as [described here](https://connexion.readthedocs.io/en/latest/routing.html#automatic-routing).
```
# with Automatic Routing
main('openapi_3.0_example.json', destdir='generated', restyresolver='api', debug=False, templatedir='templates')
```

Without restyresolver parameter Automatic Routing will not be enable and Boilerplate will be use only operationId parameter.
```
# without Automatic Routing
main('openapi_3.0_example.json', destdir='generated', debug=False, templatedir='templates')
```

You can edit templates/def.j2 inside templatedir variable (templates directory) to change default def to each method.



Now just run and it will generate Boilerplate code inside destdir.
```
python cli.py
```



