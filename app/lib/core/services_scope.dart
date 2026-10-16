import 'package:flutter/widgets.dart';

import 'app_services.dart';

/// Disponibiliza [AppServices] para a árvore e reconstrói quando Ajustes mudam.
class ServicesScope extends InheritedNotifier<AppServices> {
  const ServicesScope({super.key, required AppServices services, required super.child})
      : super(notifier: services);

  static AppServices of(BuildContext context) {
    final scope = context.dependOnInheritedWidgetOfExactType<ServicesScope>();
    assert(scope != null, 'ServicesScope não encontrado na árvore');
    return scope!.notifier!;
  }
}
