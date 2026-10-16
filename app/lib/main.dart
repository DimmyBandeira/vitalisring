import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

import 'core/app_services.dart';
import 'core/services_scope.dart';
import 'core/theme/vr_colors.dart';
import 'core/theme/vr_theme.dart';
import 'features/home/home_screen.dart';

Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();

  // App do idoso: só retrato, barras do sistema escuras.
  await SystemChrome.setPreferredOrientations([DeviceOrientation.portraitUp]);
  SystemChrome.setSystemUIOverlayStyle(const SystemUiOverlayStyle(
    statusBarColor: Colors.transparent,
    statusBarIconBrightness: Brightness.light,
    systemNavigationBarColor: VrColors.background,
    systemNavigationBarIconBrightness: Brightness.light,
  ));

  final services = await AppServices.bootstrap();
  runApp(VitalisRingApp(services: services));
}

class VitalisRingApp extends StatelessWidget {
  const VitalisRingApp({super.key, required this.services});

  final AppServices services;

  @override
  Widget build(BuildContext context) {
    return ServicesScope(
      services: services,
      child: MaterialApp(
        title: 'Vitalis Ring',
        debugShowCheckedModeBanner: false,
        theme: VrTheme.dark(),
        // Respeita o tamanho de fonte do sistema, mas com teto para não quebrar o layout.
        builder: (context, child) {
          final mq = MediaQuery.of(context);
          final scaler = mq.textScaler.clamp(minScaleFactor: 1.0, maxScaleFactor: 1.3);
          return MediaQuery(data: mq.copyWith(textScaler: scaler), child: child!);
        },
        home: const HomeScreen(),
      ),
    );
  }
}
