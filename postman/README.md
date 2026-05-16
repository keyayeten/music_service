# Postman collections

`stage1-identity-auth.postman_collection.json` содержит ручной сценарий Stage 1 + Stage 2 + Stage 3:

1. `Signup`
2. `Login (username/email)`
3. `Me`
4. `Refresh`
5. `Get My Profile`
6. `Update My Profile`
7. `Create Track`
8. `Publish Track`
9. `Create Album`
10. `Set Album Tracks`
11. `Publish Album`
12. `List Public Tracks`
13. `Get Public Track`
14. `List Public Albums`
15. `Get Public Album`

Перед запуском:

- подними приложение (`make run-native` или `make up`);
- проверь `baseUrl` в переменных коллекции;
- при необходимости измени `email`/`username` на уникальные значения.
- для проверки `PATCH /api/v1/profiles/me` назначь пользователю роль `composer` (иначе ожидается `403`);
- перед `Set Album Tracks` убедись, что `trackId` и `albumId` уже заполнены предыдущими запросами;
- публичные запросы Stage 3 (`List/Get Public ...`) можно запускать без `Authorization`.
