import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:vitalis_ring/core/app_services.dart';
import 'package:vitalis_ring/features/home/widgets/sos_hold_button.dart';
import 'package:vitalis_ring/main.dart';

void main() {
  testWidgets('fluxo SOS: conecta, segura 3 s, envia', (tester) async {
    SharedPreferences.setMockInitialValues({});
    await tester.binding.setSurfaceSize(const Size(400, 860));
    final services = await AppServices.bootstrap();

    await tester.pumpWidget(VitalisRingApp(services: services));
    expect(find.text('PROCURANDO O ANEL…'), findsOneWidget);

    await tester.pump(const Duration(seconds: 2));
    expect(find.text('CONECTADO AO ANEL'), findsOneWidget);
    await tester.pump(const Duration(seconds: 1)); // animação do número
    expect(find.text('85%'), findsOneWidget);

    // Toque rápido não dispara.
    final button = find.byType(SosHoldButton);
    final center = tester.getCenter(button);
    var g = await tester.startGesture(center);
    await tester.pump(const Duration(milliseconds: 800));
    await g.up();
    await tester.pump(const Duration(milliseconds: 300));
    expect(find.text('Chamando ajuda…'), findsNothing);

    // Segurar 3 s dispara.
    g = await tester.startGesture(center);
    for (var i = 0; i < 33; i++) {
      await tester.pump(const Duration(milliseconds: 100));
    }
    await g.up();
    await tester.pump(const Duration(milliseconds: 500));
    expect(find.text('Chamando ajuda…'), findsOneWidget);

    await tester.pump(const Duration(seconds: 2));
    await tester.pump(const Duration(milliseconds: 400));
    expect(find.text('Ajuda a caminho'), findsOneWidget);

    // Encerra timers da simulação.
    await tester.pumpWidget(const SizedBox());
    services.dispose();
    await tester.pump(const Duration(seconds: 5));
  });
}
