# IBAMA — atributos das camadas

Geoportal: [[Geosserviços/IBAMA/Instituto Brasileiro do Meio Ambiente e dos Recursos Naturais Renováveis — IBAMA|Instituto Brasileiro do Meio Ambiente e dos Recursos Naturais Renováveis — IBAMA]]

Os campos abaixo vêm de `DescribeFeatureType` (XSD), sem download de feições.

## SISCOM (6)

### `SISCOM:ibama_autos_de_infracao_p`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `objectid` | `xsd:int` | — | 0..1 |
| `seq_auto_infracao` | `xsd:int` | true | 0..1 |
| `des_status_formulario` | `` | true | 0..1 |
| `ds_sit_auto_aie` | `` | true | 0..1 |
| `sit_cancelado` | `` | true | 0..1 |
| `num_auto_infracao` | `` | true | 0..1 |
| `ser_auto_infracao` | `` | true | 0..1 |
| `cd_original_auto_infracao` | `` | true | 0..1 |
| `tipo_auto` | `` | true | 0..1 |
| `tipo_multa` | `` | true | 0..1 |
| `val_auto_infracao` | `xsd:double` | true | 0..1 |
| `fundamentacao_multa` | `` | true | 0..1 |
| `patrimonio_apuracao` | `` | true | 0..1 |
| `gravidade_infracao` | `` | true | 0..1 |
| `cd_nivel_gravidade` | `` | true | 0..1 |
| `motivacao_conduta` | `` | true | 0..1 |
| `efeito_meio_ambiente` | `` | true | 0..1 |
| `efeito_saude_publica` | `` | true | 0..1 |
| `passivel_recuperacao` | `` | true | 0..1 |
| `unid_arrecadacao` | `` | true | 0..1 |
| `des_auto_infracao` | `` | true | 0..1 |
| `dat_hora_auto_infracao` | `xsd:dateTime` | true | 0..1 |
| `forma_entrega` | `` | true | 0..1 |
| `dat_ciencia_autuacao` | `xsd:dateTime` | true | 0..1 |
| `dt_fato_infracional` | `xsd:dateTime` | true | 0..1 |
| `dt_inicio_ato_inequivoco` | `xsd:dateTime` | true | 0..1 |
| `dt_fim_ato_inequivoco` | `xsd:dateTime` | true | 0..1 |
| `ds_unid_conciliacao` | `` | true | 0..1 |
| `cod_municipio` | `xsd:int` | true | 0..1 |
| `municipio` | `` | true | 0..1 |
| `uf` | `` | true | 0..1 |
| `num_processo` | `` | true | 0..1 |
| `nu_processo_formatado` | `` | true | 0..1 |
| `cod_infracao` | `` | true | 0..1 |
| `des_infracao` | `` | true | 0..1 |
| `tipo_infracao` | `` | true | 0..1 |
| `cd_receita_auto_infracao` | `` | true | 0..1 |
| `des_receita` | `` | true | 0..1 |
| `tp_pessoa_infrator` | `` | true | 0..1 |
| `num_pessoa_infrator` | `xsd:int` | true | 0..1 |
| `nome_infrator` | `` | true | 0..1 |
| `cpf_cnpj_infrator` | `` | true | 0..1 |
| `qt_area` | `` | true | 0..1 |
| `infracao_area` | `` | true | 0..1 |
| `des_outros_tipo_area` | `` | true | 0..1 |
| `classificacao_area` | `` | true | 0..1 |
| `ds_fator_ajuste` | `` | true | 0..1 |
| `num_longitude_auto` | `xsd:double` | true | 0..1 |
| `num_latitude_auto` | `xsd:double` | true | 0..1 |
| `ds_wkt` | `` | true | 0..1 |
| `des_local_infracao` | `` | true | 0..1 |
| `ds_referencia_acao_fiscalizatoria` | `` | true | 0..1 |
| `unidade_conservacao` | `` | true | 0..1 |
| `id_sicafi_biomas_atingidos_infracao` | `` | true | 0..1 |
| `ds_biomas_atingidos` | `` | true | 0..1 |
| `seq_notificacao` | `` | true | 0..1 |
| `seq_acao_fiscalizatoria` | `` | true | 0..1 |
| `cd_acao_fiscalizatoria` | `` | true | 0..1 |
| `unid_controle` | `` | true | 0..1 |
| `tipo_acao` | `` | true | 0..1 |
| `operacao` | `` | true | 0..1 |
| `denuncia_sisliv` | `` | true | 0..1 |
| `seq_ordem_fiscalizacao` | `` | true | 0..1 |
| `ordem_fiscalizacao` | `` | true | 0..1 |
| `unid_ordenadora` | `` | true | 0..1 |
| `seq_solicitacao_recurso` | `` | true | 0..1 |
| `solicitacao_recurso` | `` | true | 0..1 |
| `operacao_sol_recurso` | `` | true | 0..1 |
| `dt_lancamento` | `xsd:dateTime` | true | 0..1 |
| `tp_ult_alteracao` | `` | true | 0..1 |
| `dt_ult_alteracao` | `xsd:dateTime` | true | 0..1 |
| `justificativa_alteracao` | `` | true | 0..1 |
| `wkt_ge_area_autuada` | `` | true | 0..1 |
| `dt_ult_alter_geom` | `xsd:dateTime` | true | 0..1 |
| `tp_origem_ge_area_autuada` | `` | true | 0..1 |
| `ds_erro_ge_area_autuada` | `` | true | 0..1 |
| `ds_wkt_ge_area_autuada_com_erro` | `` | true | 0..1 |
| `st_auto_migrado_aie` | `` | true | 0..1 |
| `ds_enquadramento_administrativo` | `` | true | 0..1 |
| `ds_enquadramento_nao_administrativo` | `` | true | 0..1 |
| `ds_enquadramento_complementar` | `` | true | 0..1 |
| `cd_termos_apreensao` | `` | true | 0..1 |
| `cd_termos_embargos` | `` | true | 0..1 |
| `tp_origem_registro_auto` | `` | true | 0..1 |
| `ultima_atualizacao_relatorio` | `xsd:dateTime` | true | 0..1 |
| `shape` | `gml:PointPropertyType` | true | 0..1 |

### `SISCOM:ibama_desembargos_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `objectid` | `xsd:int` | — | 0..1 |
| `seq_tad` | `xsd:int` | true | 0..1 |
| `num_tad` | `` | true | 0..1 |
| `ser_tad` | `` | true | 0..1 |
| `tipo_desembargo` | `` | true | 0..1 |
| `des_desembargo` | `` | true | 0..1 |
| `dat_desembargo` | `xsd:date` | true | 0..1 |
| `uf` | `` | true | 0..1 |
| `cod_municipio` | `xsd:int` | true | 0..1 |
| `municipio` | `` | true | 0..1 |
| `nome_imovel` | `` | true | 0..1 |
| `des_localizacao` | `` | true | 0..1 |
| `nome_embargado` | `` | true | 0..1 |
| `cpf_cnpj_embargado` | `` | true | 0..1 |
| `forma_entrega` | `` | true | 0..1 |
| `tipo_area` | `` | true | 0..1 |
| `seq_auto_infracao` | `xsd:int` | true | 0..1 |
| `num_auto_infracao` | `` | true | 0..1 |
| `num_processo` | `` | true | 0..1 |
| `des_tad` | `` | true | 0..1 |
| `dat_embargo` | `xsd:date` | true | 0..1 |
| `dat_impressao` | `xsd:date` | true | 0..1 |
| `dat_ult_alteracao` | `xsd:date` | true | 0..1 |
| `tipo_alteracao` | `` | true | 0..1 |
| `justificativa_alteracao` | `` | true | 0..1 |
| `operacao` | `` | true | 0..1 |
| `seq_acao_fiscalizatoria` | `xsd:int` | true | 0..1 |
| `cd_acao_fiscalizatoria` | `` | true | 0..1 |
| `ordem_fiscalizacao` | `` | true | 0..1 |
| `sit_cancelado` | `` | true | 0..1 |
| `cod_substituicao` | `` | true | 0..1 |
| `num_longitude_tad` | `xsd:double` | true | 0..1 |
| `num_latitude_tad` | `xsd:double` | true | 0..1 |
| `qtd_area_embargada` | `xsd:double` | true | 0..1 |
| `deter_prodes` | `` | true | 0..1 |
| `id_poligono` | `` | true | 0..1 |
| `embarga_poligono` | `` | true | 0..1 |
| `des_status_formulario` | `` | true | 0..1 |
| `des_status_formulario_aie` | `` | true | 0..1 |
| `seq_notificacao` | `xsd:int` | true | 0..1 |
| `seq_ordem_fiscalizacao` | `xsd:int` | true | 0..1 |
| `unid_controle` | `` | true | 0..1 |
| `unid_apresentacao` | `` | true | 0..1 |
| `unid_ordenadora` | `` | true | 0..1 |
| `seq_solicitacao_recurso` | `xsd:int` | true | 0..1 |
| `solicitacao_recurso` | `` | true | 0..1 |
| `operacao_sol_recurso` | `` | true | 0..1 |
| `dat_ult_alter_geom` | `xsd:date` | true | 0..1 |
| `origem_geom` | `` | true | 0..1 |
| `ultima_atualizacao_relatorio` | `xsd:dateTime` | true | 0..1 |
| `shape` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `st_area_shape_` | `xsd:double` | true | 0..1 |
| `st_perimeter_shape_` | `xsd:double` | true | 0..1 |

### `SISCOM:ibama_embargos_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `objectid` | `xsd:int` | — | 0..1 |
| `seq_tad` | `xsd:int` | true | 0..1 |
| `num_tad` | `` | true | 0..1 |
| `serie_tad` | `` | true | 0..1 |
| `cod_uf` | `` | true | 0..1 |
| `uf` | `` | true | 0..1 |
| `cod_municipio` | `xsd:int` | true | 0..1 |
| `municipio` | `` | true | 0..1 |
| `nome_imovel` | `` | true | 0..1 |
| `des_localizacao` | `` | true | 0..1 |
| `nome_embargado` | `` | true | 0..1 |
| `cpf_cnpj_embargado` | `` | true | 0..1 |
| `sit_desmatamento` | `` | true | 0..1 |
| `tipo_area` | `` | true | 0..1 |
| `num_auto_infracao` | `` | true | 0..1 |
| `serie_auto_infracao` | `` | true | 0..1 |
| `cod_tipo_bioma` | `` | true | 0..1 |
| `des_tipo_bioma` | `` | true | 0..1 |
| `operacao` | `` | true | 0..1 |
| `unid_controle` | `` | true | 0..1 |
| `ordem_fiscalizacao` | `` | true | 0..1 |
| `cd_acao_fiscalizatoria` | `` | true | 0..1 |
| `num_processo` | `` | true | 0..1 |
| `des_tad` | `` | true | 0..1 |
| `des_infracao` | `` | true | 0..1 |
| `num_longitude_gms_tad` | `` | true | 0..1 |
| `num_latitude_gms_tad` | `` | true | 0..1 |
| `dat_embargo` | `xsd:dateTime` | true | 0..1 |
| `dat_impressao` | `xsd:dateTime` | true | 0..1 |
| `dat_ult_alteracao` | `xsd:dateTime` | true | 0..1 |
| `num_longitude_tad` | `xsd:double` | true | 0..1 |
| `num_latitude_tad` | `xsd:double` | true | 0..1 |
| `qtd_area_desmatada` | `xsd:double` | true | 0..1 |
| `qtd_area_embargada` | `xsd:double` | true | 0..1 |
| `origem_geom` | `` | true | 0..1 |
| `dat_ult_alter_geom` | `xsd:dateTime` | true | 0..1 |
| `shape` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `st_area_shape_` | `xsd:double` | true | 0..1 |
| `st_perimeter_shape_` | `xsd:double` | true | 0..1 |

### `SISCOM:ibama_embargos_cancelados_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `objectid` | `xsd:int` | — | 0..1 |
| `seq_tad` | `xsd:int` | true | 0..1 |
| `num_tad` | `` | true | 0..1 |
| `ser_tad` | `` | true | 0..1 |
| `uf` | `` | true | 0..1 |
| `cod_municipio` | `xsd:int` | true | 0..1 |
| `municipio` | `` | true | 0..1 |
| `nome_imovel` | `` | true | 0..1 |
| `des_localizacao` | `` | true | 0..1 |
| `nome_embargado` | `` | true | 0..1 |
| `cpf_cnpj_embargado` | `` | true | 0..1 |
| `forma_entrega` | `` | true | 0..1 |
| `tipo_area` | `` | true | 0..1 |
| `seq_auto_infracao` | `xsd:int` | true | 0..1 |
| `num_auto_infracao` | `` | true | 0..1 |
| `num_processo` | `` | true | 0..1 |
| `des_tad` | `` | true | 0..1 |
| `dat_embargo` | `xsd:date` | true | 0..1 |
| `dat_impressao` | `xsd:date` | true | 0..1 |
| `dat_ult_alteracao` | `xsd:date` | true | 0..1 |
| `tipo_alteracao` | `` | true | 0..1 |
| `justificativa_alteracao` | `` | true | 0..1 |
| `operacao` | `` | true | 0..1 |
| `seq_acao_fiscalizatoria` | `xsd:int` | true | 0..1 |
| `cd_acao_fiscalizatoria` | `` | true | 0..1 |
| `ordem_fiscalizacao` | `` | true | 0..1 |
| `cod_substituicao` | `` | true | 0..1 |
| `num_longitude_tad` | `xsd:double` | true | 0..1 |
| `num_latitude_tad` | `xsd:double` | true | 0..1 |
| `qtd_area_embargada` | `xsd:double` | true | 0..1 |
| `deter_prodes` | `` | true | 0..1 |
| `id_poligono` | `` | true | 0..1 |
| `embarga_poligono` | `` | true | 0..1 |
| `des_status_formulario` | `` | true | 0..1 |
| `des_status_formulario_aie` | `` | true | 0..1 |
| `seq_notificacao` | `xsd:int` | true | 0..1 |
| `seq_ordem_fiscalizacao` | `xsd:int` | true | 0..1 |
| `unid_controle` | `` | true | 0..1 |
| `unid_apresentacao` | `` | true | 0..1 |
| `unid_ordenadora` | `` | true | 0..1 |
| `seq_solicitacao_recurso` | `xsd:int` | true | 0..1 |
| `solicitacao_recurso` | `` | true | 0..1 |
| `operacao_sol_recurso` | `` | true | 0..1 |
| `dat_ult_alter_geom` | `xsd:date` | true | 0..1 |
| `origem_geom` | `` | true | 0..1 |
| `ultima_atualizacao_relatorio` | `xsd:dateTime` | true | 0..1 |
| `shape` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `st_area_shape_` | `xsd:double` | true | 0..1 |
| `st_perimeter_shape_` | `xsd:double` | true | 0..1 |

### `SISCOM:ibama_termos_de_apreensao_p`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `objectid` | `xsd:int` | — | 0..1 |
| `seq_tad` | `xsd:int` | true | 0..1 |
| `ds_sit_apreensao` | `` | true | 0..1 |
| `st_cancelado` | `` | true | 0..1 |
| `cd_tad` | `` | true | 0..1 |
| `cd_serie_tad` | `` | true | 0..1 |
| `dt_apreensao` | `xsd:date` | true | 0..1 |
| `dt_impressao` | `xsd:date` | true | 0..1 |
| `nu_pessoa_apreensao` | `xsd:int` | true | 0..1 |
| `no_pessoa_apreensao` | `` | true | 0..1 |
| `nu_cpf_cnpj_pessoa_apreensao` | `` | true | 0..1 |
| `nu_processo_formatado` | `` | true | 0..1 |
| `ds_tad` | `` | true | 0..1 |
| `ds_complementar` | `` | true | 0..1 |
| `cd_municipio` | `xsd:int` | true | 0..1 |
| `no_municipio` | `` | true | 0..1 |
| `sg_uf` | `` | true | 0..1 |
| `ds_localizacao` | `` | true | 0..1 |
| `nu_longitude_tad` | `xsd:double` | true | 0..1 |
| `nu_latitude_tad` | `xsd:double` | true | 0..1 |
| `ds_forma_entrega` | `` | true | 0..1 |
| `sg_unidade_apresentacao` | `` | true | 0..1 |
| `sg_unidade_controle` | `` | true | 0..1 |
| `vl_tad` | `xsd:double` | true | 0..1 |
| `seq_auto_infracao` | `xsd:int` | true | 0..1 |
| `cd_auto_infracao` | `` | true | 0..1 |
| `ser_auto_infracao` | `` | true | 0..1 |
| `seq_notificacao` | `` | true | 0..1 |
| `seq_acao_fiscalizatoria` | `xsd:int` | true | 0..1 |
| `cd_acao_fiscalizatoria` | `` | true | 0..1 |
| `no_operacao` | `` | true | 0..1 |
| `seq_ordem_fiscalizacao` | `xsd:int` | true | 0..1 |
| `nu_ordem_fiscalizacao` | `` | true | 0..1 |
| `sg_unidade_ordenadora` | `` | true | 0..1 |
| `seq_solicitacao_recurso` | `xsd:int` | true | 0..1 |
| `nu_solicitacao_recurso` | `` | true | 0..1 |
| `no_operacao_sol_recurso` | `` | true | 0..1 |
| `dt_alteracao` | `xsd:date` | true | 0..1 |
| `tp_alteracao` | `` | true | 0..1 |
| `ds_justificativa_alteracao` | `` | true | 0..1 |
| `ds_wkt_local_apreensao` | `` | true | 0..1 |
| `ds_enquadramento_administrativo` | `` | true | 0..1 |
| `vl_multa` | `xsd:double` | true | 0..1 |
| `ds_auto_infracao` | `` | true | 0..1 |
| `ds_justificativa_cancelamento` | `` | true | 0..1 |
| `cd_original_apreensao` | `` | true | 0..1 |
| `ds_coordenada_apreensao` | `` | true | 0..1 |
| `ds_enquadramento_nao_administrativo` | `` | true | 0..1 |
| `ds_enquadramento_complementar` | `` | true | 0..1 |
| `tp_origem_registro_apreensao` | `` | true | 0..1 |
| `ultima_atualizacao_relatorio` | `xsd:dateTime` | true | 0..1 |
| `shape` | `gml:PointPropertyType` | true | 0..1 |

### `SISCOM:ibama_termos_de_suspensao_p`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `objectid` | `xsd:int` | — | 0..1 |
| `seq_tad` | `xsd:int` | true | 0..1 |
| `status_formulario` | `` | true | 0..1 |
| `sit_cancelado` | `` | true | 0..1 |
| `num_tad` | `` | true | 0..1 |
| `ser_tad` | `` | true | 0..1 |
| `dat_tad` | `xsd:date` | true | 0..1 |
| `dat_impressao` | `xsd:date` | true | 0..1 |
| `num_pessoa_suspensao` | `xsd:int` | true | 0..1 |
| `nom_pessoa_suspensao` | `` | true | 0..1 |
| `cpf_cnpj_pessoa_suspensao` | `` | true | 0..1 |
| `num_processo` | `` | true | 0..1 |
| `des_tad` | `` | true | 0..1 |
| `cod_municipio` | `xsd:int` | true | 0..1 |
| `nom_municipio` | `` | true | 0..1 |
| `sig_uf` | `` | true | 0..1 |
| `des_localizacao` | `` | true | 0..1 |
| `num_longitude_tad` | `xsd:double` | true | 0..1 |
| `num_latitude_tad` | `xsd:double` | true | 0..1 |
| `des_justificativa` | `` | true | 0..1 |
| `forma_entrega` | `` | true | 0..1 |
| `unid_apresentacao` | `` | true | 0..1 |
| `unid_controle` | `` | true | 0..1 |
| `seq_auto_infracao` | `xsd:int` | true | 0..1 |
| `seq_notificacao` | `xsd:int` | true | 0..1 |
| `seq_acao_fiscalizatoria` | `xsd:int` | true | 0..1 |
| `seq_ordem_fiscalizacao` | `xsd:int` | true | 0..1 |
| `num_ordem_fiscalizacao` | `` | true | 0..1 |
| `seq_solicitacao_recurso` | `xsd:int` | true | 0..1 |
| `num_solicitacao_recurso` | `` | true | 0..1 |
| `operacao_sol_recurso` | `` | true | 0..1 |
| `dat_alteracao` | `xsd:date` | true | 0..1 |
| `tipo_alteracao` | `` | true | 0..1 |
| `justificativa_alteracao` | `` | true | 0..1 |
| `ultima_atualizacao_relatorio` | `xsd:dateTime` | true | 0..1 |
| `shape` | `gml:PointPropertyType` | true | 0..1 |
