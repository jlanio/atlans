# Inter (fonte do web)

Os arquivos daqui são a Inter v20 do Google Fonts, variável, um por faixa de
caracteres: os mesmos, byte a byte, que o `next/font/google` baixava a cada
build (ver `../inter.ts`). Licença SIL Open Font License 1.1, em `OFL.txt`.

| Arquivo | Faixa | SHA-256 |
|---|---|---|
| `inter-latin.woff2` | latin | `c940764593d0fe5d596be327ca7558855e018039fb78509aa21921fd3644c3e4` |
| `inter-latin-ext.woff2` | latin-ext | `a28eb6d3ccb534ae0c94ca999371df024aab60b08c3c8a5720ee9e32fa0faaa2` |
| `inter-cyrillic.woff2` | cyrillic | `aebf2ab4a4ce6810d73c1ac7be7cafb4e5ec4cee2d6db5fb3e09691747ec4bd6` |
| `inter-cyrillic-ext.woff2` | cyrillic-ext | `fccca918fea40089dacadc7045861314d1a6bc91f1f323cc1eeb22ebcdb321b5` |
| `inter-greek.woff2` | greek | `46dd4cdca58c26ae87cc6927657bf83b2e8abfc39ffd0ab176e301a8d28d22bf` |
| `inter-greek-ext.woff2` | greek-ext | `a2e2c783ca6f9c20486e81e72a279203e86730bbf8f01ff6a5ee9dbd09e1c271` |
| `inter-vietnamese.woff2` | vietnamese | `8db00ff46c67b22cda8bed865acf7077651cac8d2841d5b40980556b48961931` |

Para trocar de versão: pedir o CSS com o mesmo agente do Next (é ele que faz o
Google responder `woff2`), baixar o `url(...)` de cada faixa, conferir os
`unicode-range` do CSS contra os de `../inter.ts` e atualizar esta tabela.

```sh
curl -A "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/104.0.0.0 Safari/537.36" \
  "https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap"
```
