# VEÍCULOS 10 SUL — Android GPS v1 (piloto)

Aplicativo Android nativo (Android 8+) integrado ao Controle de Veículos existente. Instalador inicial em `../downloads/VEICULOS_10_SUL_GPS_v1.apk`, assinado para testes. Não inclui chaves Supabase, dados do banco ou segredos.

## Uso

1. Instale e abra **VEÍCULOS 10 SUL**. O atalho do navegador continua sendo a versão web.
2. Registre a saída normalmente. Confirme **Iniciar GPS** e permita localização **precisa** e notificações.
3. O serviço de localização com notificação permanente acompanha a viagem com a tela bloqueada ou a interface fechada. Após 5 minutos de posições válidas sem deslocamento, pergunta se a viagem terminou.
4. **Parada temporária** mantém a viagem aberta; o próximo deslocamento volta a somar distância e habilita outro alerta na próxima parada. Sem resposta, a viagem continua aberta.
5. **Finalizar viagem** pede confirmação, encerra o GPS e abre o retorno com o KM estimado. Confira o hodômetro e confirme no sistema para liberar o veículo.
6. Sem internet o GPS continua somando localmente. A confirmação de retorno depende de internet; a distância fica preservada até a confirmação.

O GPS estima distância e não lê o hodômetro. Pontos imprecisos, saltos impossíveis e intervalos sem posições não são somados. Oscilações de um celular parado não acrescentam KM. Interrupções geram aviso para conferir o hodômetro. Forçar parada do aplicativo, reiniciar o telefone, revogar permissões ou certas restrições de bateria podem interromper o serviço. Reabrir permite retomar sem inventar distância no intervalo perdido. Nenhuma coleta é iniciada fora de uma viagem autorizada pelo motorista. As coordenadas são utilizadas no cálculo local e não são transmitidas ao banco.

## Compilação e testes

Java 17, Android SDK 35 e Gradle 8.9: `gradle -p android assembleDebug`. Plugin Android 8.7.3. O APK fornecido foi compilado diretamente com Android SDK 35, `aapt2`, `javac`, `d8`, `zipalign` e `apksigner`. A chave de assinatura fica fora do Git; esta é uma versão de teste, sem publicação na Play Store.

`tests/TripEngineTest.java` cobre oscilações parado, alerta de 5 minutos, parada temporária, retomada, novo alerta, sinal interrompido, saltos, baixa precisão, ida e volta e posições fora de ordem. `../test_gps_bridge.py` cobre vinculação ao ID da movimentação e distâncias inválidas. Compilação, testes e verificação de assinatura passaram. Ainda não validado em aparelho físico.

Teste de campo: registrar saída real, bloquear a tela, percorrer um trajeto conhecido, parar 5 minutos, marcar temporária, fazer a volta, finalizar e conferir o hodômetro. Conferir também perda de sinal, falta de internet, retomada da internet e retorno confirmado em outro navegador.
