/**
 * Indicador de atividade do nó em execução — quatro barras oscilando fora de
 * fase.
 *
 * Substituiu o spinner girando (`TbLoader`/`TbLoader2`). Rotação é o glifo
 * universal de "aguarde", e o que este badge precisa dizer é outra coisa: que
 * há trabalho ACONTECENDO ali dentro. A oscilação fora de fase lê como
 * atividade — processamento, cálculo — em vez de espera.
 *
 * Um SVG local e não um ícone da `react-icons`: nenhum glifo do Tabler tem esta
 * forma, e a animação precisa atingir cada barra com um atraso próprio, o que
 * exige controlar os elementos internos. A animação em si mora no `globals.css`
 * (`.exec-activity`), junto com os demais estados de execução — inclusive a
 * degradação sob `prefers-reduced-motion`.
 */
const ExecActivity = ({ size = 14, className }: { size?: number; className?: string }) => (
  <svg
    width={size}
    height={size}
    viewBox="0 0 24 24"
    className={className ? `exec-activity ${className}` : "exec-activity"}
    aria-hidden="true"
    focusable="false"
  >
    <g fill="currentColor">
      <rect x="3"    y="5" width="3.4" height="14" rx="1.7" />
      <rect x="8.3"  y="5" width="3.4" height="14" rx="1.7" />
      <rect x="13.6" y="5" width="3.4" height="14" rx="1.7" />
      <rect x="18.9" y="5" width="3.4" height="14" rx="1.7" />
    </g>
  </svg>
)

export default ExecActivity
