# shellcheck shell=bash
# scripts/lib/ui.sh
# The terminal interface of bootstrap.sh and up.sh: language, colors, the
# numbered stages, the questions and the final panel.
#
# Sourced, not run. Works on bash 3.2 (macOS): no associative arrays, no
# ${var,,}. The texts live in scripts/lib/i18n/<lang>.sh as M_<key> variables;
# `t <key> [args]` prints one, with printf-style %s arguments.
#
# Without a terminal (CI, a pipe) or with NO_COLOR set, it prints plain text:
# no colors, no spinner, no cursor movement.

UI_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
UI_LANGS="pt en es"

# ── Colors and glyphs ────────────────────────────────────────────────────────
ui_init_colors() {
    if [ -t 1 ] && [ -z "${NO_COLOR:-}" ] && [ "${TERM:-}" != "dumb" ]; then
        UI_COLOR=1
        C_RESET=$'\033[0m'; C_BOLD=$'\033[1m'; C_DIM=$'\033[2m'
        C_ACCENT=$'\033[38;5;209m'; C_OK=$'\033[32m'; C_WARN=$'\033[33m'
        C_ERR=$'\033[31m'; C_INFO=$'\033[36m'
    else
        UI_COLOR=0
        C_RESET=""; C_BOLD=""; C_DIM=""; C_ACCENT=""; C_OK=""; C_WARN=""; C_ERR=""; C_INFO=""
    fi
    # Box-drawing characters only where the terminal speaks UTF-8.
    case "${LC_ALL:-${LC_CTYPE:-${LANG:-}}}" in
        *UTF-8*|*utf8*|*UTF8*|*utf-8*)
            G_OK="✓"; G_ERR="✗"; G_WARN="!"; G_INFO="·"; G_ASK="?"; G_DONE="●"; G_NOW="◉"; G_TODO="○"
            G_SKIP="◌"; G_LINE="━"; G_RULE="─"; G_TL="╭"; G_TR="╮"; G_BL="╰"; G_BR="╯"; G_V="│"
            UI_SPIN="⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏" ;;
        *)
            G_OK="ok"; G_ERR="x"; G_WARN="!"; G_INFO="-"; G_ASK="?"; G_DONE="*"; G_NOW="@"; G_TODO="o"
            G_SKIP="-"; G_LINE="="; G_RULE="-"; G_TL="+"; G_TR="+"; G_BL="+"; G_BR="+"; G_V="|"
            UI_SPIN="|/-\\" ;;
    esac
}
ui_init_colors

# ── Language ─────────────────────────────────────────────────────────────────
# pt is the reference catalog: it is always loaded first, so a key missing from
# another language falls back to Portuguese instead of printing nothing.
ui_lang_load() {
    local lang="$1"
    case " $UI_LANGS " in *" $lang "*) ;; *) lang="pt" ;; esac
    # shellcheck source=i18n/pt.sh
    . "$UI_DIR/i18n/pt.sh"
    if [ "$lang" != "pt" ]; then
        # shellcheck disable=SC1090
        . "$UI_DIR/i18n/$lang.sh"
    fi
    # shellcheck disable=SC2034 # read by the scripts that source this file
    UI_LANG="$lang"
}

# The language of the system (LANG/LC_ALL), mapped to one we have.
ui_lang_guess() {
    case "${LC_ALL:-${LC_MESSAGES:-${LANG:-}}}" in
        pt*) echo pt ;;
        es*) echo es ;;
        en*) echo en ;;
        *) echo pt ;;
    esac
}

t() {  # <key> [args...]: the text in the current language
    local key="M_$1" fmt
    shift
    fmt="${!key:-$key}"
    # shellcheck disable=SC2059
    printf "$fmt" "$@"
}

# ── Wrapping ─────────────────────────────────────────────────────────────────
# The width the text may take: the terminal's (at most 82), minus the margin.
ui_width() {
    local cols
    cols="$(tput cols 2>/dev/null || echo 80)"
    case "$cols" in ''|*[!0-9]*) cols=80 ;; esac
    [ "$cols" -gt 82 ] && cols=82
    echo $((cols - 6))
}
# ui_wrap <width> <text>: the text in lines of at most <width> characters,
# broken between words (a longer word stays whole).
ui_wrap() {
    local width="$1" word line=""
    local -a words
    read -r -a words <<< "$2"
    for word in "${words[@]}"; do
        if [ -z "$line" ]; then
            line="$word"
        elif [ $(( ${#line} + 1 + ${#word} )) -le "$width" ]; then
            line="$line $word"
        else
            printf '%s\n' "$line"
            line="$word"
        fi
    done
    [ -n "$line" ] && printf '%s\n' "$line"
    return 0
}
# _ui_lines <first prefix> <next prefix> <color> <text>: the text wrapped, the
# first line after one prefix and the others after the other.
_ui_lines() {
    local first="$1" next="$2" color="$3" l n=0
    while IFS= read -r l; do
        if [ "$n" = 0 ]; then printf '%s%s%s%s\n' "$first" "$color" "$l" "$C_RESET"
        else printf '%s%s%s%s\n' "$next" "$color" "$l" "$C_RESET"; fi
        n=1
    done < <(ui_wrap "$(( $(ui_width) - 2 ))" "$4")
}

# ── Lines ────────────────────────────────────────────────────────────────────
ui_ok()   { _ui_lines "  $C_OK$G_OK$C_RESET " "    " "" "$*"; }
ui_info() { _ui_lines "  $C_DIM$G_INFO$C_RESET " "    " "" "$*"; }
ui_warn() { _ui_lines "  $C_WARN$G_WARN$C_RESET " "    " "" "$*"; }
ui_err()  { _ui_lines "  $C_ERR$G_ERR$C_RESET " "    " "" "$*" >&2; }
ui_hint() { _ui_lines "    " "    " "$C_DIM" "$*"; }
ui_bullet() { _ui_lines "    • " "      " "" "$*"; }
ui_cmd()  { printf '    %s$%s %s\n' "$C_DIM" "$C_RESET" "$*"; }
ui_blank() { printf '\n'; }

# ── Banner ───────────────────────────────────────────────────────────────────
ui_banner() {  # <subtitle>
    printf '\n'
    printf '  %s%s▲ Atlans%s  %s%s%s\n' "$C_BOLD" "$C_ACCENT" "$C_RESET" "$C_DIM" "$1" "$C_RESET"
    printf '  %s%s%s\n' "$C_DIM" "$(ui_repeat "$G_RULE" 56)" "$C_RESET"
}

ui_repeat() {  # <char> <n>
    local s="" i=0
    while [ "$i" -lt "$2" ]; do s="$s$1"; i=$((i + 1)); done
    printf '%s' "$s"
}

# ── Stages ───────────────────────────────────────────────────────────────────
# The stages of a script are declared once (ui_stages "key1 key2 ..."), each key
# naming the title M_stage_<key>. ui_stage <key> opens one: a progress line with
# a dot per stage (done, current, to do, skipped) and the title. ui_skip <key>
# marks a stage as not applicable (e.g. the domain, in dev).
UI_STAGES=""
UI_SKIPPED=" "
ui_stages() { UI_STAGES="$1"; UI_SKIPPED=" "; }
ui_skip() { UI_SKIPPED="$UI_SKIPPED$1 "; }
ui_stage() {  # <key>
    local key="$1" s n=0 total=0 cur=0 dots="" mark color
    for s in $UI_STAGES; do total=$((total + 1)); [ "$s" = "$key" ] && cur=$total; done
    for s in $UI_STAGES; do
        n=$((n + 1))
        if [ "$n" -lt "$cur" ]; then
            case "$UI_SKIPPED" in *" $s "*) mark="$G_SKIP"; color="$C_DIM" ;; *) mark="$G_DONE"; color="$C_OK" ;; esac
        elif [ "$n" -eq "$cur" ]; then
            mark="$G_NOW"; color="$C_ACCENT"
        else
            case "$UI_SKIPPED" in *" $s "*) mark="$G_SKIP" ;; *) mark="$G_TODO" ;; esac
            color="$C_DIM"
        fi
        dots="$dots$color$mark$C_RESET"
        [ "$n" -lt "$total" ] && dots="$dots$C_DIM$G_LINE$G_LINE$C_RESET"
    done
    printf '\n  %s  %s%s/%s%s\n' "$dots" "$C_DIM" "$cur" "$total" "$C_RESET"
    printf '  %s%s%s\n\n' "$C_BOLD" "$(t "stage_$key")" "$C_RESET"
}

# ── Spinner ──────────────────────────────────────────────────────────────────
# ui_run <label> <command...>: runs the command with its output in a log file,
# a spinner while it runs and, at the end, ✓ or ✗ with the time it took. On a
# failure the last lines of the log go to the screen. Returns the command's code.
UI_LOG="${TMPDIR:-/tmp}/atlans-$$.log"
# On the way out, even on Ctrl+C: the cursor back, the log and the files
# registered with ui_cleanup (temporary secrets) gone.
UI_CLEAN=""
ui_cleanup() { UI_CLEAN="$UI_CLEAN $1"; }
_ui_exit() {
    [ "${UI_COLOR:-0}" = "1" ] && printf '\033[?25h'
    # shellcheck disable=SC2086
    rm -f "$UI_LOG" $UI_CLEAN
}
trap _ui_exit EXIT
ui_run() {
    local label="$1" pid code start elapsed i=0 frame
    shift
    start=$SECONDS
    if [ "$UI_COLOR" = "1" ]; then
        "$@" >"$UI_LOG" 2>&1 &
        pid=$!
        # Hide the cursor while spinning (_ui_exit gives it back on Ctrl+C).
        printf '\033[?25l'
        while kill -0 "$pid" 2>/dev/null; do
            frame="${UI_SPIN:$((i % ${#UI_SPIN})):1}"
            printf '\r  %s%s%s %s %s(%ss)%s ' "$C_ACCENT" "$frame" "$C_RESET" "$label" "$C_DIM" "$((SECONDS - start))" "$C_RESET"
            i=$((i + 1))
            sleep 0.1
        done
        set +e; wait "$pid"; code=$?; set -e
        printf '\r\033[K\033[?25h'
    else
        printf '  %s %s...\n' "$G_INFO" "$label"
        set +e; "$@" >"$UI_LOG" 2>&1; code=$?; set -e
    fi
    elapsed=$((SECONDS - start))
    if [ "$code" = "0" ]; then
        printf '  %s%s%s %s %s(%ss)%s\n' "$C_OK" "$G_OK" "$C_RESET" "$label" "$C_DIM" "$elapsed" "$C_RESET"
    else
        printf '  %s%s%s %s %s(%ss)%s\n' "$C_ERR" "$G_ERR" "$C_RESET" "$label" "$C_DIM" "$elapsed" "$C_RESET" >&2
        tail -n 15 "$UI_LOG" | sed 's/^/      /' >&2
    fi
    return "$code"
}

# ── Questions ────────────────────────────────────────────────────────────────
# All of them read from /dev/tty and print the question on stderr, so that
# $(ui_ask ...) captures only the answer.
ui_ask() {  # <text> [default]: the answer, never empty
    local answer
    while :; do
        if [ -n "${2:-}" ]; then
            printf '  %s%s%s %s %s[%s]%s ' "$C_ACCENT" "$G_ASK" "$C_RESET" "$1" "$C_DIM" "$2" "$C_RESET" >&2
            IFS= read -r answer </dev/tty
            answer="${answer:-$2}"
        else
            printf '  %s%s%s %s ' "$C_ACCENT" "$G_ASK" "$C_RESET" "$1" >&2
            IFS= read -r answer </dev/tty
        fi
        [ -n "$answer" ] && break
    done
    printf '%s' "$answer"
}
ui_ask_optional() {  # <text>: the answer, maybe empty
    local answer
    printf '  %s%s%s %s %s(%s)%s ' "$C_ACCENT" "$G_ASK" "$C_RESET" "$1" "$C_DIM" "$(t ask_optional)" "$C_RESET" >&2
    IFS= read -r answer </dev/tty
    printf '%s' "$answer"
}
ui_ask_secret() {  # <text>: not echoed, never empty
    local answer
    while :; do
        printf '  %s%s%s %s ' "$C_ACCENT" "$G_ASK" "$C_RESET" "$1" >&2
        IFS= read -r -s answer </dev/tty
        printf '\n' >&2
        [ -n "$answer" ] && break
    done
    printf '%s' "$answer"
}
ui_ask_port() {  # <text> <default>
    local answer
    while :; do
        answer="$(ui_ask "$1" "$2")"
        printf '%s' "$answer" | grep -qE '^[0-9]{1,5}$' && [ "$answer" -le 65535 ] && break
        ui_hint "$(t ask_port_invalid)" >&2
    done
    printf '%s' "$answer"
}
ui_ask_host() {  # <text> [default]: a host name, without scheme or path
    local answer
    while :; do
        answer="$(ui_ask "$1" "${2:-}")"
        printf '%s' "$answer" | grep -qE '^[A-Za-z0-9]([A-Za-z0-9.-]*[A-Za-z0-9])?$' && break
        ui_hint "$(t ask_host_invalid)" >&2
    done
    printf '%s' "$answer"
}

# ui_menu <text> <default> <value|description>...: a numbered list; the person
# types the number or the value. Prints the chosen value. With value||label the
# value is internal and only the label is shown.
ui_menu() {
    local text="$1" default="$2" item value desc n answer i def_n=1
    shift 2
    printf '  %s%s%s %s\n' "$C_ACCENT" "$G_ASK" "$C_RESET" "$text" >&2
    n=0
    for item in "$@"; do
        n=$((n + 1))
        value="${item%%|*}"; desc="${item#*|}"
        [ "$value" = "$default" ] && def_n=$n
        if [ "$desc" = "$item" ]; then
            printf '    %s%s)%s %s\n' "$C_ACCENT" "$n" "$C_RESET" "$value" >&2
        elif [ "${desc#|}" != "$desc" ]; then
            # value||label: an internal value, only the label is shown.
            printf '    %s%s)%s %s\n' "$C_ACCENT" "$n" "$C_RESET" "${desc#|}" >&2
        else
            printf '    %s%s)%s %-12s %s%s%s\n' "$C_ACCENT" "$n" "$C_RESET" "$value" "$C_DIM" "$desc" "$C_RESET" >&2
        fi
    done
    while :; do
        printf '    %s %s[%s]%s ' "$(t ask_choose)" "$C_DIM" "$def_n" "$C_RESET" >&2
        IFS= read -r answer </dev/tty
        answer="${answer:-$def_n}"
        i=0
        for item in "$@"; do
            i=$((i + 1))
            value="${item%%|*}"
            if [ "$answer" = "$i" ] || [ "$answer" = "$value" ]; then
                printf '%s' "$value"
                return
            fi
        done
        ui_hint "$(t ask_choose_invalid "$n")" >&2
    done
}

ui_confirm() {  # <text> <default y|n>: returns 0 for yes
    local answer yes no hint
    yes="$(t yes_letter)"; no="$(t no_letter)"
    if [ "$2" = "y" ]; then hint="$(printf '%s/%s' "$(printf '%s' "$yes" | tr '[:lower:]' '[:upper:]')" "$no")"
    else hint="$(printf '%s/%s' "$yes" "$(printf '%s' "$no" | tr '[:lower:]' '[:upper:]')")"; fi
    while :; do
        printf '  %s%s%s %s %s[%s]%s ' "$C_ACCENT" "$G_ASK" "$C_RESET" "$1" "$C_DIM" "$hint" "$C_RESET" >&2
        IFS= read -r answer </dev/tty
        answer="$(printf '%s' "${answer:-$2}" | tr '[:upper:]' '[:lower:]')"
        case "$answer" in
            y|yes|s|sim|si|"$yes") return 0 ;;
            n|no|nao|não|"$no") return 1 ;;
        esac
    done
}

# ── Panel ────────────────────────────────────────────────────────────────────
# ui_panel <title> <line>...: a rounded box. Lines are plain text (colors would
# break the width); a line starting with "$ " is shown as a command.
ui_panel() {
    local title="$1" line w=0 len pad max l
    local -a lines=()
    shift
    # Long lines wrap; commands, blank and indented lines stay as they are.
    max="$(( $(ui_width) - 4 ))"
    for line in "$@"; do
        case "$line" in
            '$ '*|''|'  '*) lines+=("$line") ;;
            *)
                if [ "${#line}" -le "$max" ]; then
                    lines+=("$line")
                else
                    while IFS= read -r l; do lines+=("$l"); done < <(ui_wrap "$max" "$line")
                fi ;;
        esac
    done
    set -- "${lines[@]}"
    for line in "$title" "$@"; do
        len=${#line}
        [ "$len" -gt "$w" ] && w=$len
    done
    w=$((w + 2))
    printf '\n  %s%s%s%s%s\n' "$C_DIM" "$G_TL" "$(ui_repeat "$G_RULE" "$w")" "$G_TR" "$C_RESET"
    pad=$((w - ${#title} - 1))
    printf '  %s%s%s %s%s%s%s%*s%s%s%s\n' "$C_DIM" "$G_V" "$C_RESET" "$C_BOLD" "$C_ACCENT" "$title" "$C_RESET" "$pad" "" "$C_DIM" "$G_V" "$C_RESET"
    for line in "$@"; do
        pad=$((w - ${#line} - 1))
        case "$line" in
            '$ '*) printf '  %s%s%s %s%s%s%*s%s%s%s\n' "$C_DIM" "$G_V" "$C_RESET" "$C_INFO" "$line" "$C_RESET" "$pad" "" "$C_DIM" "$G_V" "$C_RESET" ;;
            *) printf '  %s%s%s %s%*s%s%s%s\n' "$C_DIM" "$G_V" "$C_RESET" "$line" "$pad" "" "$C_DIM" "$G_V" "$C_RESET" ;;
        esac
    done
    printf '  %s%s%s%s%s\n' "$C_DIM" "$G_BL" "$(ui_repeat "$G_RULE" "$w")" "$G_BR" "$C_RESET"
}
