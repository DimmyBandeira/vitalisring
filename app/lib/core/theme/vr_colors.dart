import 'package:flutter/material.dart';

/// Tokens do tema escuro (console noturno) de `site/design/tokens.css`.
/// Fonte única de cor do app — não usar literais nas telas.
abstract final class VrColors {
  static const background = Color(0xFF0E0C0A); // um tom abaixo de --vr-dark p/ o brilho do botão
  static const surface = Color(0xFF16130F); // --vr-dark
  static const card = Color(0xFF1F1B16); // --vr-white (dark)
  static const line = Color(0xFF3A342B); // --vr-line (dark)

  static const gold = Color(0xFFD2AC5A); // --vr-bronze (dark)
  static const goldLight = Color(0xFFE3C37E); // --vr-bronze-700 (dark)
  static const champagne = Color(0xFFC9A24B); // decorativo

  static const ink = Color(0xFFFCF8EE); // texto principal
  static const inkSoft = Color(0xFFCFC6B4); // texto secundário

  // Status semânticos (nunca dourado). Sempre com ícone + texto.
  static const ok = Color(0xFF3FBF6E); // verde clareado p/ contraste no escuro
  static const warn = Color(0xFFF2B600);
  static const alert = Color(0xFFE8710A);
  static const critical = Color(0xFFC62828);
  static const criticalBright = Color(0xFFE53935);
}
