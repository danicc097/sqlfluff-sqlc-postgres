# sqlc plugin for SQLFluff

This plugin works with [SQLFluff](https://pypi.org/project/sqlfluff/) to correctly parse and compile SQL files specific to
[sqlc](https://github.com/kyleconroy/sqlc) with Postgres dialect.

To get started, install the plugin with

```bash
python -m pip install --upgrade --force-reinstall git+https://github.com/danicc097/sqlfluff-sqlc-postgres
```
and it will be registered as a plugin for SQLFluff. To start using it, update your config with the new keys. 

###### `.sqlfluff`
```cfg
[sqlfluff]
templater=sqlfluff-sqlc-postgres

[sqlfluff:templater:sqlfluff-sqlc-postgres]
param_style=sqlc
autofill_missing_params=True # infer params not in cfg based on ::type syntax
log_param_replacements=True # show every placeholder
```

Then start using it with:

```bash
sqlfluff lint --dialect postgres ./<folder_containing_sql>
```

You will know what's being done under the hood:

```sql
SELECT * FROM "users" 
WHERE "id" = @id::int AND "is_verified" = @is_verified::boolean;
```
```log
Replacing id with: 1000
Replacing is_verified with: true
```

```sql
SELECT * FROM "users" 
WHERE "id" = @id AND "is_verified" = @is_verified;
```
```
No type was specified for parameter id. Assuming text.
Replacing id with: 'string'
No type was specified for parameter is_verified. Assuming text.
Replacing is_verified with: 'string'
```

With explicit parameters, substitutions are shown by default.

###### `.sqlfluff`
```cfg
[sqlfluff:templater:sqlfluff-sqlc-postgres]
  ...
level_condition= > 10
```

```sql
SELECT * FROM "users" WHERE "id" = @id AND "level" @level_condition;
```
```
No type was specified for parameter id. Assuming text.
Replacing @id with: 'string'
Replacing @level_condition with: > 10
```


For more details on how to configure plugins, [see the documentation](https://docs.sqlfluff.com/en/stable/configuration.html#dbt-project-configuration).
