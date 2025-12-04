Banco de dados do MySQL 

[whatsapp_db_webhook]

- webhook
    - id 
    - date 
    - json 
- contacts
    - id 
    - wa_id 
    - profile # (human, bot, ia) 
    - name 
    - create_in
    - activate_bot # true or false
    - activate_automatic_message # true or false
    - create_for_phone_number 
    - last_message_timestamp
- settings
    - id
    - default_bot
    - default_profile # human
    - wa_id
    - phone_number_id 
    - webhook_verify_token 
    - meta_token
    - organization_id
- organization
    - id 
    - create_in 
    - activate # true or false
    - create_by # id_user
    - organization_name
- users
    - id
    - name 
    - create_in
    - email 
    - password
    - activate
- organization_users
    - id
    - organization_id
    - user_id
    - create_in
    - role # user / user_admin / user_creator 
    - activate # true
-  chat_session_message
    - id 
    - wa_id # wa_id de quem enviou a mensagem 
    - wa_id_received # wa_id de quem recebeu a mensagem
    - phone_number_id # id do numero da conversa
    - session_id # uuid
    - flow_state # se aplicavel o status do flow (json)
    - message_status # status da mensagem 
    - is_user_message # se a mensgaem foi enviada pelo usuario 
    - bot_replied # se a mensagem foi respondida pelo BOT
    - content # conteudo da mensagem 
    - payload # payload da API 
    - create_in # quando a mensagem foi criada (enviada)
    - updated_at # quando a mensagem foi atualizada 
    - expires_at # quando a mensagem foi expirada 
    - is_active # se a sessão esta ativa 
* sobre as sessões: quando o usuario enviar uma mensagem, caso seja a primeira dele o sistema ira criar uma sessão de chat, essa sessão tem a duração de 24h des da ultima mensagem enviada, na sessão teremos wa_id (id de quem enviou), wa_id_received (id de quem recebeu), phone_number_id (id do numero do settings) 
Ex: 
Numero do cliente: 556181500586
Meu numero: 556181412286 (phone_number_id: 524386454098961)

Suponhamos que eu com o numero +55 61 9 8150 0586 (wa_id: 556181500586) enviei mensagem para o +55 61 9 8141 2286 (wa_id: 556181412286) 

sera criado uma sessão de 24h des da última mensagem enviada pelo cliente. 

enquanto estiver com a sessão ativa ( o sitema vai verificar a ultima mensagem enviada pelo sistema e vai ver o expires_at)
se estiver expirada ele deixa a mensagem com is_active false e cria uma outra sesão 

* 