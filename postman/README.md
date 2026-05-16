# Postman collections

`music-service-api.postman_collection.json` содержит ручной сценарий Stage 1 + Stage 2 + Stage 3 + Stage 4 + Stage 5 + Stage 6 + Stage 7 + Stage 8:

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
16. `Create Playlist`
17. `Add Playlist Track`
18. `Reorder Playlist Tracks`
19. `Publish Playlist Visibility`
20. `List Public Playlists`
21. `Get Public Playlist`
22. `Add Library Item`
23. `List My Library Items`
24. `Delete Library Item`
25. `Like Track`
26. `Like Track Again (Idempotent)`
27. `Comment Track`
28. `Reply To Comment`
29. `List Track Comments`
30. `Get Track Comment By Id`
31. `List Library Favorites (After Like Sync)`
32. `Unlike Track`
33. `Get Public Track (Counters After Social)`
34. `Click External Link`
35. `Get Track Recommendations (Optional Auth)`
36. `Login Moderator (username/email)`
37. `Create Report`
38. `List Reports As User (Forbidden)`
39. `List Reports As Moderator`
40. `Get Report By Id As Moderator`
41. `Set Report Status In Review`
42. `Set Report Status Resolved`
43. `List Public Albums (Cache Warmup)`
44. `List Public Albums (Cache Hit Expectation)`
45. `List Public Playlists (Cache Warmup)`
46. `List Public Playlists (Cache Hit Expectation)`

Перед запуском:

- подними приложение (`make run-native` или `make up`);
- проверь `baseUrl` в переменных коллекции;
- при необходимости измени `email`/`username` на уникальные значения.
- для проверки `PATCH /api/v1/profiles/me` назначь пользователю роль `composer` (иначе ожидается `403`);
- перед `Set Album Tracks` убедись, что `trackId` и `albumId` уже заполнены предыдущими запросами;
- публичные запросы Stage 3 (`List/Get Public ...`) можно запускать без `Authorization`.
- перед сценариями Stage 4 проверь, что `trackId` заполнен (используется для добавления в плейлист и медиатеку);
- `Create Playlist` стартует как `private`, после `Publish Playlist Visibility` плейлист виден в `List/Get Public Playlist`.
- Stage 5 (`Like/Comment`) выполняется авторизованным пользователем и ожидает, что `trackId` указывает на уже опубликованный трек.
- `Reply To Comment` использует `commentId`, который автоматически заполняется после запроса `Comment Track`.
- Запросы чтения комментариев Stage 5 (`List Track Comments`, `Get Track Comment By Id`) требуют `Authorization`.
- `List Library Favorites (After Like Sync)` позволяет проверить автосинхронизацию лайка в `library_items`.
- перед `Click External Link` убедись, что `externalLinkId` заполнен UUID ссылки из `external_links` для опубликованного трека.
- `Get Track Recommendations (Optional Auth)` можно запускать как с `Authorization`, так и без него:
  - c токеном ожидается персонализированная выдача при наличии истории;
  - без токена возвращается fallback `top published`.
- для Stage 7 заранее создай отдельного пользователя-модератора:
  - зарегистрируй пользователя с `moderatorUsername` / `moderatorEmail`;
  - назначь ему роль `moderator` в БД (например, SQL insert в `user_roles`);
  - после этого запрос `Login Moderator (username/email)` заполнит `moderatorAccessToken`.
- `Create Report` использует `target_id = {{trackId}}`, поэтому `trackId` должен ссылаться на существующий трек.
- `List Reports As User (Forbidden)` должен вернуть `403` и подтвердить RBAC-ограничение.
- `Set Report Status In Review` и `Set Report Status Resolved` запускай строго по порядку для проверки lifecycle `open -> in_review -> resolved`.
- Stage 8 cache smoke:
  - сначала запусти `List Public Albums (Cache Warmup)`, затем `List Public Albums (Cache Hit Expectation)`;
  - сначала запусти `List Public Playlists (Cache Warmup)`, затем `List Public Playlists (Cache Hit Expectation)`;
  - ожидаемый результат: оба запроса возвращают `200`, второй запрос выполняется как проверка cache hit.
