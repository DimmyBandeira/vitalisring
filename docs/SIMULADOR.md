# Simulador e regras demonstrativas

O simulador em `/app/simulador` é restrito a profissionais autenticados e
trabalha somente com entradas digitadas e rotuladas como fictícias. Estado,
movimento, sono, duração e qualidade não são apresentados como medições reais.

As funções puras ficam em `webapp/alerts/rules.py`. Todos os valores estão em
`webapp/alerts/thresholds.py`, com o aviso: “limiares iniciais — validar
clinicamente antes de uso real”. `is_demo=False` desliga a avaliação automática.
Qualidade sintética abaixo do mínimo retorna “sem conclusão”.

As prévias de WhatsApp e e-mail usam exatamente o nível visual e nunca incluem
BPM, SpO₂ ou limiares. O número `192` aparece apenas no nível crítico por ser o
contato público de emergência.

Evidências: 96 testes aprovados, incluindo tabela de limites/durações,
qualidade insuficiente, bloqueio de dado real e interface autenticada.
