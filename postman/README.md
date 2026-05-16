# Postman collections

`stage1-identity-auth.postman_collection.json` содержит ручной сценарий Stage 1 + Stage 2:

1. `Signup`
2. `Login (username/email)`
3. `Me`
4. `Refresh`
5. `Get My Profile`
6. `Update My Profile`

Перед запуском:

- подними приложение (`make run-native` или `make up`);
- проверь `baseUrl` в переменных коллекции;
- при необходимости измени `email`/`username` на уникальные значения.
- для проверки `PATCH /api/v1/profiles/me` назначь пользователю роль `composer` (иначе ожидается `403`).
