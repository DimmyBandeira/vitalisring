import 'package:flutter/material.dart';

import 'vr_colors.dart';

abstract final class VrTheme {
  static const bodyFont = 'Atkinson';
  static const displayFont = 'Cormorant';

  static ThemeData dark() {
    const scheme = ColorScheme.dark(
      primary: VrColors.gold,
      onPrimary: VrColors.surface,
      secondary: VrColors.champagne,
      surface: VrColors.surface,
      onSurface: VrColors.ink,
      error: VrColors.criticalBright,
    );

    return ThemeData(
      useMaterial3: true,
      colorScheme: scheme,
      scaffoldBackgroundColor: VrColors.background,
      fontFamily: bodyFont,
      // Corpo mínimo 18px (diretriz do design system para o público idoso).
      textTheme: const TextTheme(
        bodyLarge: TextStyle(fontSize: 20, height: 1.5, color: VrColors.ink),
        bodyMedium: TextStyle(fontSize: 18, height: 1.5, color: VrColors.ink),
        bodySmall: TextStyle(fontSize: 16, height: 1.4, color: VrColors.inkSoft),
        titleLarge: TextStyle(fontSize: 24, fontWeight: FontWeight.w700, color: VrColors.ink),
      ),
      appBarTheme: const AppBarTheme(
        backgroundColor: VrColors.surface,
        foregroundColor: VrColors.ink,
        elevation: 0,
        titleTextStyle: TextStyle(
          fontFamily: bodyFont,
          fontSize: 20,
          fontWeight: FontWeight.w700,
          color: VrColors.ink,
        ),
      ),
      switchTheme: SwitchThemeData(
        thumbColor: WidgetStateProperty.resolveWith(
          (s) => s.contains(WidgetState.selected) ? VrColors.surface : VrColors.inkSoft,
        ),
        trackColor: WidgetStateProperty.resolveWith(
          (s) => s.contains(WidgetState.selected) ? VrColors.gold : VrColors.line,
        ),
      ),
      inputDecorationTheme: const InputDecorationTheme(
        border: OutlineInputBorder(),
        enabledBorder: OutlineInputBorder(borderSide: BorderSide(color: VrColors.line)),
        focusedBorder: OutlineInputBorder(borderSide: BorderSide(color: VrColors.gold, width: 2)),
        labelStyle: TextStyle(color: VrColors.gold),
      ),
    );
  }
}
