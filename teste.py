import pyodbc
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import asyncio
from datetime import datetime, timedelta
import pandas as pd



# Configuração da conexão com o Google Sheets
def get_google_sheets_client(credentials_path):
    scope = [
        "https://spreadsheets.google.com/feeds",
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive.file",
        "https://www.googleapis.com/auth/drive",
    ]
    creds = ServiceAccountCredentials.from_json_keyfile_name(credentials_path, scope)
    return gspread.authorize(creds)

# Configuração da conexão com o banco de dados
connection_string_wis = """
DSN=WIS;
UID=joh_gomes;
PWD=Zaqezis9i9H!u;
DBQ=WIS;
DBA=W;
APA=T;
EXC=F;
FEN=T;
QTO=T;
FRC=10;
FDL=10;
LOB=T;
RST=T;
BTD=F;
BNF=F;
BAM=IfAllSuccessful;
NUM=NLS;
DPM=F;
MTS=T;
MDI=F;
CSR=F;
FWC=F;
FBS=64000;
TLO=O;
MLD=0;
ODA=F;
"""

connection_string_dw = """
DRIVER={Oracle in OraClient11g_home1};
SERVER=MLPDW;
UID=RAT_SOUSA;
PWD=Ro160215%;
DBQ=MLPDW;
DBA=W;
APA=T;
EXC=F;
XSM=Default;
FEN=T;
QTO=T;
FRC=10;
FDL=10;
LOB=T;
RST=T;
BTD=F;
BNF=F;
BAM=IfAllSuccessful;
NUM=NLS;
DPM=F;
MTS=T;
MDI=Me;
CSR=F;
FWC=F;
FBS=60000;
TLO=O;
MLD=0;
ODA=F;
"""

# Função para consultar o banco de dados
async def fetch_data_from_db(query, connection_string):
    try:
        conn = pyodbc.connect(connection_string, autocommit=True)
        cursor = conn.cursor()
        cursor.execute(query)
        rows = cursor.fetchall()
        return [[str(cell) for cell in row] for row in rows]
    except pyodbc.Error as e:
        print(f"Erro ao conectar: {e}")
        return []
    finally:
        if 'conn' in locals():
            conn.close()

# Função para atualizar o Google Sheets
async def update_google_sheet(data, sheet_key, worksheet_name, start_cell):
    client = get_google_sheets_client('credentials.json')
    worksheet = client.open_by_key(sheet_key).worksheet(worksheet_name)
    worksheet.batch_clear([start_cell])
    worksheet.update(data, start_cell)
    print(f"Dados atualizados da tabela {worksheet_name} às {datetime.now().strftime(format='%d/%m/%Y %H:%M')}")

# Função para processar a atualização de status da operação
async def update_status_operacao():
    query = """
WITH PROGRAMADO AS
                  (SELECT TO_CHAR(MIN(CBP.DT_ADDROW), 'dd/MM/rrrr') AS DATA_CORTE,
                          CBP.CD_CARGA AS LOTE,
                          MIN(CBP.CD_SITUACAO) AS CD_SITUACAO,
                          SUM(DTP.QT_SEPARAR-NVL(DTP.QT_CANCELADA,0)) AS PRO,
                          COUNT(DISTINCT CBP.NU_PEDIDO_ORIGEM) AS PEDIDOS,
                          SUM((CAP.VL_ALTURA * CAP.VL_LARGURA * CAP.VL_PROFUNDIDADE*DTP.QT_SEPARAR)/1000000) AS CUB_PROGRAMADA
                   FROM WIS50.T_CAB_PEDIDO_SAIDA CBP
                   INNER JOIN WIS50.T_DET_PEDIDO_SAIDA DTP ON CBP.CD_EMPRESA = DTP.CD_EMPRESA
                   AND CBP.NU_PEDIDO_ORIGEM = DTP.NU_PEDIDO_ORIGEM
                   AND DTP.CD_SITUACAO <> 68
                   INNER JOIN WIS50.T_CAB_PRODUTO CAP ON DTP.CD_PRODUTO = CAP.CD_PRODUTO
                   AND CBP.NU_PEDIDO_ORIGEM = DTP.NU_PEDIDO_ORIGEM
                   WHERE CBP.CD_EMPRESA = 12650
                     AND CBP.DT_ADDROW >= SYSDATE-5
                     AND CBP.CD_SITUACAO NOT IN (68)
                     AND NOT (CBP.CD_SITUACAO <> 64
                              AND DTP.CD_SITUACAO = 64)
                   GROUP BY CBP.CD_CARGA),
                     DTS AS
                  (SELECT DSS.CD_CARGA,
                          SUM(NVL(DSS.QT_SEPARADO,0)) AS SEPARADO,
                          SUM(NVL(DSS.QT_CONFERIDO,0)) AS CONFERIDO,
                          SUM((CAP.VL_ALTURA * CAP.VL_LARGURA * CAP.VL_PROFUNDIDADE*(NVL(DSS.QT_SEPARADO,0)))/1000000) AS CUB_SEPARADA,
                          SUM((CAP.VL_ALTURA * CAP.VL_LARGURA * CAP.VL_PROFUNDIDADE*(NVL(DSS.QT_CONFERIDO,0)))/1000000) AS CUB_CONFERIDA
                   FROM WIS50.T_DET_SEPARACAO DSS
                   INNER JOIN WIS50.T_CAB_PRODUTO CAP ON DSS.CD_PRODUTO = CAP.CD_PRODUTO
                   WHERE DSS.CD_EMPRESA = 12650
                     AND DSS.DT_ADDROW >= SYSDATE-5
                   GROUP BY DSS.CD_CARGA)
                SELECT PROGRAMADO.DATA_CORTE,
                       PROGRAMADO.LOTE,
                       PROGRAMADO.PRO AS PROGRAMACAO,
                       PROGRAMADO.CUB_PROGRAMADA,
                       PROGRAMADO.PEDIDOS,
                       PROGRAMADO.CD_SITUACAO,
                       NVL(DTS.SEPARADO,0) AS SEPARADO,
                       NVL(DTS.CUB_SEPARADA,0) AS CUB_SEPARADA,
                       NVL(DTS.CONFERIDO,0) CONFERIDO,
                       NVL(DTS.CUB_CONFERIDA,0) CUB_CONFERIDA,
                       NVL(PROGRAMADO.PRO - DTS.SEPARADO,0) AS PENDENTE_SEP,
                       NVL(PROGRAMADO.CUB_PROGRAMADA - DTS.CUB_SEPARADA,0) AS CUB_PENDENTE_SEP,
                       NVL(PROGRAMADO.PRO - DTS.CONFERIDO,0) AS PENDENTE_CONF,
                       NVL(PROGRAMADO.CUB_PROGRAMADA - DTS.CUB_CONFERIDA,0) AS CUB_PENDENTE_CONF
                FROM PROGRAMADO
                LEFT JOIN DTS ON DTS.CD_CARGA = PROGRAMADO.LOTE
                ORDER BY DATA_CORTE
    """
    data = await fetch_data_from_db(query, connection_string_wis)
    await update_google_sheet(data, '19wq-kacGtgwRS8ZMUpDofA4rpOEMO4r_1SGBtcc7oxM', 'STATUS_OPERAÇÃO', 'A2:N')

# Função para processar a atualização de produção por turno
async def update_producao_turno():
    query = """
SELECT DT_COMPETENCIA
         , CD_CARGA
         , TURNO
         , SUM(SEPARADO) AS QT_SEPARADO
         , trunc(SUM(CUB_TOTAL),2) AS CUBAGEM
         , HORA
    FROM(SELECT DS.CD_EMPRESA
         , TO_CHAR(DS.DT_SEPARACAO             , 'YYYY-MM-DD') DATA_SEPARACAO
         , CASE WHEN TO_CHAR(DS.DT_SEPARACAO, 'HH24') BETWEEN  0 AND 5  THEN TO_CHAR(DS.DT_SEPARACAO-1,'YYYY-MM-DD')
                WHEN TO_CHAR(DS.DT_SEPARACAO, 'HH24') BETWEEN 22 AND 23 THEN TO_CHAR(DS.DT_SEPARACAO  ,'YYYY-MM-DD')
                WHEN TO_CHAR(DS.DT_SEPARACAO, 'HH24') BETWEEN  14 AND 21 THEN TO_CHAR(DS.DT_SEPARACAO  ,'YYYY-MM-DD')
                WHEN TO_CHAR(DS.DT_SEPARACAO, 'HH24') BETWEEN  6 AND 13 THEN TO_CHAR(DS.DT_SEPARACAO  ,'YYYY-MM-DD')
           END AS DT_COMPETENCIA
         , TO_CHAR(DS.DT_SEPARACAO, 'HH24') AS HORA
         , CASE WHEN TO_CHAR(DS.DT_SEPARACAO, 'HH24') BETWEEN  0 AND 5  THEN '3 TURNO'
                WHEN TO_CHAR(DS.DT_SEPARACAO, 'HH24') BETWEEN 22 AND 23 THEN '3 TURNO'
                WHEN TO_CHAR(DS.DT_SEPARACAO, 'HH24') BETWEEN  14 AND 21 THEN '2 TURNO'
                WHEN TO_CHAR(DS.DT_SEPARACAO, 'HH24') BETWEEN  6 AND 13 THEN '1 TURNO'
           END AS TURNO
         , ROUND(DS.QT_SEPARADO ,0) AS SEPARADO
         , ROUND(DS.QT_CONFERIDO,0) AS CONFERIDO
         , PS.CD_CARGA
         , (CB.VL_ALTURA*CB.VL_LARGURA*CB.VL_PROFUNDIDADE)/1000000 AS CUB_TOTAL
         
    FROM WIS50.T_DET_SEPARACAO      DS
       , WIS50.T_CAB_PEDIDO_SAIDA   PS
       , WIS50.T_CAB_PRODUTO        CB

    WHERE DS.CD_EMPRESA     = PS.CD_EMPRESA
      AND DS.NU_PEDIDO      = PS.NU_PEDIDO
      AND DS.CD_PRODUTO     = CB.CD_PRODUTO
      AND DS.CD_EMPRESA = 12650
      AND PS.TP_PEDIDO NOT IN ('RMN')
      AND TRUNC(TO_DATE(CASE WHEN TO_CHAR(DS.DT_SEPARACAO, 'HH24') BETWEEN  0 AND 5  THEN TO_CHAR(DS.DT_SEPARACAO-1,'YYYY-MM-DD')
                WHEN TO_CHAR(DS.DT_SEPARACAO, 'HH24') BETWEEN 22 AND 23 THEN TO_CHAR(DS.DT_SEPARACAO  ,'YYYY-MM-DD')
                WHEN TO_CHAR(DS.DT_SEPARACAO, 'HH24') BETWEEN  14 AND 21 THEN TO_CHAR(DS.DT_SEPARACAO  ,'YYYY-MM-DD')
                WHEN TO_CHAR(DS.DT_SEPARACAO, 'HH24') BETWEEN  6 AND 13 THEN TO_CHAR(DS.DT_SEPARACAO  ,'YYYY-MM-DD')
           END,'YYYY-MM-DD')) >= TRUNC(sysdate-2)
      AND DS.QT_SEPARADO > 0)
      
      GROUP BY DT_COMPETENCIA
             , CD_CARGA
             , TURNO
             , HORA
    ORDER BY DT_COMPETENCIA, TURNO
    """
    data = await fetch_data_from_db(query, connection_string_wis)
    await update_google_sheet(data, '19wq-kacGtgwRS8ZMUpDofA4rpOEMO4r_1SGBtcc7oxM', 'PRODUÇÃO_TURNO', 'A2:F')

async def update_pendencia_590():
    query = '''
SELECT
  TO_CHAR(ENT.DT_CONFERENCIA, 'DD/MM/YYYY HH24:MI') AS DATA_ENTRADA ,
  ENT.CD_AGENDA,
  ENT.NU_ETIQUETA_LOTE ETIQUETA,
  ROUND(TRUNC(SYSDATE) - TRUNC(ENT.DT_ADDROW)) DIAS,
  ENT.CD_PRODUTO,
  (
    SELECT
      CAB.DS_PRODUTO
    FROM
      WIS50.T_CAB_PRODUTO CAB
    WHERE
      ENT.CD_PRODUTO = CAB.CD_PRODUTO
  ) DS_PRODUTO,
  FUNC.NM_FUNCIONARIO,
  ENT.QT_CONFERIDO,
  'AGRUPADA' TP_ETIQUETA,
  ENT.CD_ENDERECO
FROM
  WIS50.T_DET_ETIQUETA_LOTE ENT
INNER JOIN WIS50.T_FUNCIONARIO FUNC ON ENT.CD_FUNC_CONFERENCIA = FUNC.CD_FUNCIONARIO
WHERE
  ENT.CD_EMPRESA = 1590
  AND ENT.CD_SITUACAO = 23
  AND ENT.CD_PRODUTO <> '11'
UNION ALL
SELECT
  TO_CHAR(ENT.DT_CONFERENCIA, 'DD/MM/YYYY HH24:MI') AS DATA_ENTRADA,
  ENT.CD_AGENDA,
  ENT.NU_ETIQUETA,
  ROUND(TRUNC(SYSDATE) - TRUNC(ENT.DT_ADDROW)) DIAS,
  ENT.CD_PRODUTO,
  (
    SELECT
      CAB.DS_PRODUTO
    FROM
      WIS50.T_CAB_PRODUTO CAB
    WHERE
      ENT.CD_PRODUTO = CAB.CD_PRODUTO
  ) DS_PRODUTO,
  FUNC.NM_FUNCIONARIO,
  ENT.QT_CONFERIDO,
  'NORMAL' TP_ETIQUETA,
  ENT.CD_ENDERECO
FROM
  WIS50.T_ETIQUETA_ENTRADA ENT
INNER JOIN WIS50.T_FUNCIONARIO FUNC ON ENT.CD_FUNC_CONFERENCIA = FUNC.CD_FUNCIONARIO
WHERE
  ENT.CD_EMPRESA = 1590
  AND ENT.CD_SITUACAO = 23
  AND ENT.CD_PRODUTO <> '11'
  AND ENT.CD_AREA_ARMAZ NOT IN (17, 9, 27)
ORDER BY
  DATA_ENTRADA
  
    '''
    data = await fetch_data_from_db(query, connection_string_wis)
    await update_google_sheet(data, '1M12Q3mTBCfElEw6ACUOGYBGyzlacIFA_ZmAdVWRmDco', 'BASE', 'A2:s')

async def update_grade():
    query = """
with base as (
    select distinct
           mp.numpedven,
           mp.tpnota,
           DECODE(mp.TIPOPED, 0,'VENDAS',2  ,'ABA') AS TIPO_PEDIDO,
           mp.filorig,
           mp.codfil,
           mp.dtpedido,
           mp.fllibfat,
           mp.numlote,
           mp.dtentrega,
           mp.codfiltransffat,
           dtlibfat,
           mik.coditprodkit || ci.digitprod item,
           mik.coditprodkit coditprod,
           mik.qtcomp,
           cp.descricao,
           (ce.altura * ce.largura * ce.comp)/1000000 cub_unit,
           mp.sitcarga,
           mp.codreserva,
           cl.descricao linha,
           cf.descricao familia,
           mp.dtalter,
           mp.praca,
           mp.numpedcli,
           mp.codrota,
           mp.codmodal,
           mo.descricao modalidade,
           mp.codcli,
           mik.precounit,
           mik.qtcomp * mik.precounit vltotal,
            to_date(CASE WHEN MP.CODFIL = 200
                        THEN (SELECT TO_CHAR(DTHORA_INT,'YYYY-MM-DD HH24:MI:SS') 
                              FROM GEMCO.INT_SITE_MOV_PEDIDO@producao 
                             WHERE NUMPEDVEN = MP.NUMPEDVEN 
                               AND ROWNUM = 1)  
                               else to_char(MP.HRPEDIDO,'YYYY-MM-DD HH24:MI:SS') end, 'yyyy-mm-dd HH24:MI:SS') as  DTLIBFAT_MOD
            from GEMCO.MOV_PEDIDO@producao mp,
                 GEMCO.MOV_ITPED_KIT@producao mik,
                 GEMCO.CAD_ITPROD@producao ci,
                 GEMCO.CAD_PROD@producao cp,
                 GEMCO.CAD_PRODLOC@producao pro,
                 GEMCO.CAD_EMBAL@producao ce,
                 GEMCO.CAD_LINHA@producao cl,
                 GEMCO.CAD_FAMILIA@producao cf,
                 GEMCO.CAD_MODAL@producao mo
           where mp.sitcarga in (0, 1, 2, 8, 9, 14) 
             and ((mp.tpnota in (55,536,655,665) and mp.status = 4) 
                 or (mp.tpnota  = 51 and mp.status = 5 and
                 nvl(mp.fltransffatnf, 'X') <> 'S'))
             and mp.tpped = 'E'
             and mp.codfil = mik.codfil
             and mp.tipoped = mik.tipoped
             and mp.numpedven = mik.numpedven
             and mik.coditprodkit = ci.coditprod
             and ci.codprod = cp.codprod
             and mp.filorig = pro.codfil
             and mik.coditprodkit = pro.coditprod
             and cp.codprod = ce.codprod
             and nvl(cp.codtpserv, 0) = 0 
             and mp.filorig =2650
             and ce.codembal = mik.codembal
             and ci.codlinha = cl.codlinha
             and ci.codfam = cf.codfam
             and mp.codmodal = mo.codmodal(+)
             AND NVL(MP.FLCREDLISTA, 'X') <> 'G'    
     union all        
    select distinct
           mp.numpedven,
           mp.tpnota,    
           DECODE(mp.TIPOPED, 0,'VENDAS',2  ,'ABA') AS TIPO_PEDIDO,  
           mp.filorig,
           mp.codfil,
           mp.dtpedido,
           mp.fllibfat,
           mp.numlote,
           mp.dtentrega,
           mp.codfiltransffat,

           dtlibfat,
           mi.coditprod || ci.digitprod item,
           mi.coditprod,
           mi.qtcomp,
           cp.descricao,
           (ce.altura * ce.largura * ce.comp)/1000000 cub_unit,
           mp.sitcarga,
           mp.codreserva,
           cl.descricao linha,
           cf.descricao familia,
           mp.dtalter,
           mp.praca,
           mp.numpedcli,
           mp.codrota,
           mp.codmodal,
           mo.descricao modalidade,
           mp.codcli,
           mi.precounit,
           mi.qtcomp * mi.precounit vltotal,
            to_date(CASE WHEN MP.CODFIL = 200
                        THEN (SELECT TO_CHAR(DTHORA_INT,'YYYY-MM-DD HH24:MI:SS') 
                              FROM GEMCO.INT_SITE_MOV_PEDIDO@producao 
                             WHERE NUMPEDVEN = MP.NUMPEDVEN 
                               AND ROWNUM = 1)  
                               else to_char(MP.HRPEDIDO,'YYYY-MM-DD HH24:MI:SS') end, 'yyyy-mm-dd HH24:MI:SS') as  DTLIBFAT_MOD
            from GEMCO.MOV_PEDIDO@producao mp,
                 GEMCO.MOV_ITPED@producao mi,
                 GEMCO.CAD_ITPROD@producao ci,
                 GEMCO.CAD_PROD@producao cp,
                 GEMCO.CAD_PRODLOC@producao pro,
                 GEMCO.CAD_EMBAL@producao ce,
                 GEMCO.CAD_LINHA@producao cl,
                 GEMCO.CAD_FAMILIA@producao cf,
                 GEMCO.CAD_MODAL@producao mo
           where mp.sitcarga in (0, 1, 2, 8, 9, 14) 
             and ((mp.tpnota in (55,536,655,665) and mp.status = 4) -- pedidos de abastecimento
                 or (mp.tpnota = 51 and mp.status = 5 and
                 nvl(mp.fltransffatnf, 'X') <> 'S')) -- pedidos de vendas
             and mp.tpped = 'E'
             and mp.codfil = mi.codfil
             and mp.tipoped = mi.tipoped
             and mp.numpedven = mi.numpedven
             and nvl(mi.flmovitpedkit, 'X') <> 'S'
             and mi.coditprod = ci.coditprod
             and ci.codprod = cp.codprod
             and mp.filorig = pro.codfil
             and mi.coditprod = pro.coditprod
             and cp.codprod = ce.codprod
             and nvl(cp.codtpserv, 0) = 0 
             and mp.filorig =2650
             and ce.codembal = mi.codembal
             and ci.codlinha = cl.codlinha
             and ci.codfam = cf.codfam
             and mp.codmodal = mo.codmodal(+)
             AND NVL(MP.FLCREDLISTA, 'X') <> 'G')
    ,
    BASE_2 AS (
    select CASE WHEN x.fllibfat = 'N' THEN '1-Nao Liberado'
                WHEN x.sitcarga = 2   THEN '6-Conferido Aguardando Fat'
                WHEN x.sitcarga = 8   THEN '8-Venda Pendente SEFAZ'
                WHEN x.sitcarga = 9   THEN '9-Bloqueado Expedicao'
                WHEN x.sitcarga = 14  THEN '14-Eficiencia Energetica'
                WHEN xx.flseparacao = 'N' THEN '3-Lote montado'
                WHEN xx.flseparacao IN ('B', 'R') THEN '4-Lote em Separacao'
                WHEN xx.flseparacao = 'C' THEN '5-Lote em Conferencia'
                ELSE '2-Liberado'
           END AS STATUS,
           xx.flseparacao,
           (select c.descricao
                from GEMCO.CAD_PRACA@producao a,
                     GEMCO.CAD_PRACAROTA@producao b,
                     GEMCO.CAD_ROTAENTREGA@producao c
               where a.praca = b.praca
                 and b.codrota = c.codrota
                 and a.praca = x.praca) as descricaorota,
                 trunc(Res.Dtentrega) Preventrega,
           case when x.fllibfat = 'N' THEN (CASE WHEN Res.Codsitprod IN ('AD', 'AN') THEN 'Adicional'
                                                 WHEN Res.Codsitprod = 'EC' THEN 'Encomenda'
                                                 WHEN Res.Tipopedido = 'T' OR res.codreservay IS NOT NULL THEN 'Roteiro Y'
                                                 WHEN Res.Codsitprod NOT IN ('AD', 'AN', 'EC') AND Res.Tipopedido = 'C' THEN 'Pedido de Compra'
                                                   END) END AS SITUACAO,
                                          RES.NUMPEDCOMP,
           decode(nvl(x.numlote, 0), 0, 'EM CARTEIRA', 'EM PROCESSO') as status_operacao,
        CASE 
            WHEN x.DTLIBFAT_MOD IS NULL AND x.DTENTREGA >= x.DTPEDIDO THEN x.DTENTREGA
            WHEN x.DTPEDIDO IS NULL AND x.DTENTREGA >= x.DTLIBFAT_MOD THEN x.DTENTREGA
            WHEN x.DTENTREGA IS NULL AND x.DTLIBFAT_MOD >= x.DTPEDIDO THEN x.DTLIBFAT_MOD
            WHEN x.DTPEDIDO IS NULL AND x.DTLIBFAT_MOD >= x.DTENTREGA THEN x.DTLIBFAT_MOD
            WHEN x.DTENTREGA IS NULL AND x.DTPEDIDO >= x.DTLIBFAT_MOD THEN x.DTPEDIDO
            WHEN x.DTLIBFAT_MOD IS NULL AND x.DTPEDIDO >= x.DTENTREGA THEN x.DTPEDIDO
            ELSE GREATEST(x.DTLIBFAT_MOD, x.DTPEDIDO, x.DTENTREGA)
        END AS Dt_MAxima,
           x.*
           
                
    FROM base x
    left join gemco.dis_lote@producao xx on xx.nlote(+) = x.numlote and xx.codfil(+) = x.filorig
    left join GEMCO.MOV_ITRESERVA@producao Res on res.Codreserva = x.Codreserva
                                     and res.Coditprod = x.coditprod
                                     and Rownum = 1
    where x.fllibfat = 'S' and x.codfiltransffat not in (98))

    SELECT 
    NUMPEDVEN,
    TPNOTA,
    TIPO_PEDIDO,
    CODFILTRANSFFAT,
    DECODE(CODFIL, 200, 'SITE', 'REDE') AS CANAL_VENDAS,
    CODMODAL,
    DESCRICAO,
    MODALIDADE,
        CASE WHEN DESCRICAOROTA = 'NORTE' AND CODMODAL = 'COU' THEN 'SEDEX'
             WHEN DESCRICAOROTA = 'NORTE' AND CODMODAL <> 'COU' THEN 'FAVORITA'
             ELSE DESCRICAOROTA END AS DESCRICAOROTA,
    DTALTER DATA_APROVACAO,
    DTPEDIDO,
    DTENTREGA,
    PREVENTREGA,
    DTLIBFAT_MOD,
    FAMILIA,
    FILORIG,
    STATUS,
    ITEM,
    LINHA,
    NUMLOTE,
    NUMPEDCOMP,
    QTCOMP,
    PRECOUNIT,
    CUB_UNIT,
    status_operacao,
    SITUACAO,

    CASE WHEN SITUACAO='Roteiro Y' or SITUACAO='Roteiro Y ABA'

    then 'ROT Y'

    WHEN FLLIBFAT = 'N'

    THEN 'VENDA FORNECEDOR'

    WHEN FLLIBFAT ='S' AND Dt_Maxima > (SYSDATE+2) THEN 'PROGRAMADO'
    WHEN CODMODAL ='INA' THEN 'ABA INAUGURACAO'
    WHEN SITUACAO ='Roteiro Y' or  SITUACAO='Roteiro Y ABA' THEN 'ROT Y'
    WHEN FLLIBFAT ='S' AND sitcarga = 9 THEN 'BLOQUEADO'
    WHEN FLLIBFAT ='N' THEN 'VENDA FORNECEDOR'
    WHEN FLLIBFAT ='S' THEN status_operacao ELSE status_operacao

    END AS STATUS_OPERACAO_GERENCIAL,
    CUB_UNIT * QTCOMP CUBTOTAL,
    PRECOUNIT * QTCOMP VALTOTAL

    from
    BASE_2 xxx
    """
    data = await fetch_data_from_db(query, connection_string_dw)
    await update_google_sheet(data, '19wq-kacGtgwRS8ZMUpDofA4rpOEMO4r_1SGBtcc7oxM', 'CARTEIRA', 'A2:ac')

async def update_wis_production():
    query ="""
    SELECT

DET.CD_EMPRESA AS CD,
EE.RUA,
EE.CD_ENDERECO,

TO_CHAR(DET.DT_SEPARACAO, 'DD/MM/YYYY HH24:MI:SS') AS DT_SEPARACAO,
TO_CHAR(DET.DT_SEPARACAO, 'DD/MM/YYYY') AS DATA_SEPARACAO,
CASE EE.DS_POSTO
        WHEN 'MOVEIS  (28 - 33)' THEN 'MOVEIS'
        WHEN 'COFRE' THEN 'COFRE'
        WHEN  'DIVERSOS P (04 A 14)'  THEN 'DIVERSOS'
        WHEN 'COLCHAO & ESTOFADO G18- G21)' THEN 'COLCHAO & ESTOFADO'
        WHEN 'PICKING COURIER (DIVERSOS)' THEN 'COURIER'
        WHEN 'LINHA BRANCA (21 - 27)' THEN 'LINHA BRANCA'
        WHEN 'TV + PNEU RUA 16 A 18' THEN 'TV E PNEU'
        WHEN 'MERCADO' THEN 'BENS DE CONSUMO'
        WHEN 'PICKING STAGER (ELETRO+ESTOFADO+COLCHAO)' THEN 'GRANPICK'
        WHEN 'GENERICO+DOCA+TEC' THEN 'GENERICO'
        ELSE EE.DS_POSTO
    END AS POSTO,
TR.CD_FUNCIONARIO AS ID,
FU.NM_FUNCIONARIO AS NOME,



CASE        WHEN TO_CHAR(DET.DT_SEPARACAO, 'HH24') BETWEEN  0 AND 5  THEN '3 TURNO'
            WHEN TO_CHAR(DET.DT_SEPARACAO, 'HH24') BETWEEN 22 AND 23 THEN '3 TURNO'
            WHEN TO_CHAR(DET.DT_SEPARACAO, 'HH24') BETWEEN  14 AND 21 THEN '2 TURNO'
            WHEN TO_CHAR(DET.DT_SEPARACAO, 'HH24') BETWEEN  6 AND 13 THEN '1 TURNO'
       END AS TURNO,

CAB.NU_PEDIDO_ORIGEM,
TO_CHAR(DET.DT_SEPARACAO, 'HH24') AS HS24,
SUM(DET.QT_SEPARADO) AS QTDE_SEPARADA,
REPLACE(TO_CHAR(SUM(DET.QT_SEPARADO * (CAB.VL_ALTURA * CAB.VL_LARGURA * CAB.VL_PROFUNDIDADE) / 1000000), '99999999.999999'), '.', ',') AS "M3_SEPARADO",
DET.CD_PRODUTO,
CAB.DS_PRODUTO,
FA.DS_FAMILIA,
LI.DS_LINHA,
EE.PREDIO,
TO_CHAR(EE.COLUNA,'000') AS N_COLUNA,
EE.QUADRANTE,
EE.NIVEL,
--(REPLACE(TO_CHAR((CAB.VL_ALTURA * CAB.VL_LARGURA * CAB.VL_PROFUNDIDADE) / 1000000, '9999999999.99'), '.', ',')) AS "CUBAGEM_UNITARIA",                            
 DET.CD_CARGA AS LOTE,
 TR.NU_TAREFA AS TAREFA,
 DET.NU_SEPARACAO AS SEPARACAO,
 DET.CD_GRUPO_SEPARACAO,
 DET.CD_ENDERECO_DESTINO AS DOCA,
 TO_CHAR(DET.DT_SEPARACAO, 'HH24:MI:SS') AS HORA_SEPARACAO


FROM
                            (SELECT CD_EMPRESA, DT_SEPARACAO,NU_SEPARACAO,NU_PEDIDO, CD_PRODUTO, CD_ENDERECO,CD_CARGA,NU_CONTENEDOR,CD_CLIENTE,CD_FUNCIONARIO,QT_SEPARADO,CD_GRUPO_SEPARACAO,NU_TAREFA,CD_ENDERECO_DESTINO
                            FROM WIS50.T_DET_SEPARACAO
                            WHERE CD_EMPRESA = 12650) DET

LEFT JOIN                        (SELECT CD_EMPRESA, NU_PEDIDO, NU_PEDIDO_ORIGEM, TP_PEDIDO, CD_CLIENTE,CD_TRANSPORTADORA
                            FROM WIS50.T_CAB_PEDIDO_SAIDA
                            WHERE CD_EMPRESA = 12650) CAB ON DET.CD_EMPRESA = CAB.CD_EMPRESA AND DET.NU_PEDIDO = CAB.NU_PEDIDO

LEFT JOIN                   (SELECT CD_EMPRESA, NU_TAREFA, CD_FUNCIONARIO, VARIAVEL, CD_ENDERECO_ORIGEM, CD_ENDERECO_DESTINO
                            FROM WIS50.T_TAREFAS_REALIZADAS
                            WHERE CD_EMPRESA = 12650
                            AND CD_APLICACAO LIKE 'CSE020%'
                            AND NU_TAREFA IS NOT NULL) TR ON DET.CD_EMPRESA = TR.CD_EMPRESA AND DET.NU_TAREFA = TR.NU_TAREFA AND DET.CD_FUNCIONARIO = TR.CD_FUNCIONARIO
                            
LEFT JOIN                   (SELECT CD_FUNCIONARIO, NM_FUNCIONARIO, NM_ABREV_FUNC
                            FROM WIS50.T_FUNCIONARIO) FU ON TR.CD_FUNCIONARIO = FU.CD_FUNCIONARIO
                            
                            
                            
LEFT JOIN                   (SELECT
                                  EE.CD_ENDERECO,
                                  SUBSTR(EE.CD_ENDERECO, 1, 1) AS PREDIO,
                                  SUBSTR(EE.CD_ENDERECO, 1, 3) AS RUA,
                                  SUBSTR(EE.CD_ENDERECO, 4, 3) AS COLUNA,
                                  SUBSTR(EE.CD_ENDERECO, 7, 3) AS NIVEL2,
                                  SUBSTR(EE.CD_ENDERECO, 10, 3) AS SALA,
                            CASE
                                    WHEN SUBSTR(EE.CD_ENDERECO, 1, 1) = 'P' THEN
                            CASE
                                    WHEN SUBSTR(EE.CD_ENDERECO, 4, 3) BETWEEN '000' AND '037' THEN '1 BLOCO'
                                    WHEN SUBSTR(EE.CD_ENDERECO, 4, 3) BETWEEN '038' AND '075' THEN '2 BLOCO'
                                    WHEN SUBSTR(EE.CD_ENDERECO, 4, 3) BETWEEN '076' AND '199' THEN '3 BLOCO'
                                    ELSE ''
                            END
                                    WHEN SUBSTR(EE.CD_ENDERECO, 1, 1) IN ('B', 'G') THEN
                            CASE
                                    WHEN SUBSTR(EE.CD_ENDERECO, 4, 3) BETWEEN '000' AND '033' THEN '1 BLOCO'
                                    WHEN SUBSTR(EE.CD_ENDERECO, 4, 3) BETWEEN '034' AND '067' THEN '2 BLOCO'
                                    WHEN SUBSTR(EE.CD_ENDERECO, 4, 3) BETWEEN '068' AND '199' THEN '3 BLOCO'
                            ELSE ''
                            END
                            ELSE ''
                            END AS QUADRANTE
                            ,
                            
                            CASE WHEN MOD(TO_NUMBER(SUBSTR(EE.CD_ENDERECO, 4, 3)), 2) = 0 THEN 'PAR' ELSE 'IMPAR' END AS POSICAO,
                                
                                
                                EE.CD_EMPRESA,
                                EE.CD_CLASSE,
                                CLASSEE.DS_CLASSE_PRODUTO,
                                 DECODE(EE.ID_ENDERECO_BAIXO, 'S', 'BAIXO', 'N', 'ALTO') AS NIVEL,
                                 DECODE(EE.CD_SITUACAO, '42', 'VAZIO', '45', 'OCUPADO','47', 'OCUPADO') AS SITUACAO,
                                 
                                 
                                EE.CD_AREA_ARMAZ,
                                TPA.DS_AREA_ARMAZ,
                                EE.CD_TIPO_ENDERECO,
                                TPE.DS_TIPO_ENDERECO,
                                TPT.DS_POSTO
                                
                                
                                
                                FROM WIS50.T_ENDERECO_ESTOQUE EE
                                LEFT JOIN (SELECT CD_CLASSE,DS_CLASSE, CASE 
        WHEN CD_CLASSE LIKE '26ACE' THEN 'ACESSORIOS'
        WHEN CD_CLASSE LIKE '26AER' THEN 'AEROSOL & INFLAMAVEIS'
        WHEN CD_CLASSE LIKE '26ALM' THEN 'ALIMENTOS'
        WHEN CD_CLASSE LIKE '26BEB' THEN 'BEBIDAS'
        WHEN CD_CLASSE LIKE '26BDC' THEN 'BENS DE CONSUMO'
        WHEN CD_CLASSE LIKE '26COF' THEN 'COFRE DIVERSOS'
        WHEN CD_CLASSE LIKE '26COL' THEN 'COLCHAO BOX'
        WHEN CD_CLASSE LIKE '26DIV' THEN 'DIVERSOS'
        WHEN CD_CLASSE LIKE '26ECC' THEN 'ESTOFADOS'
        WHEN CD_CLASSE LIKE '26FAR' THEN 'FARMACIA'
        WHEN CD_CLASSE LIKE '26HIG' THEN 'HIGIENE'
        WHEN CD_CLASSE LIKE '26EIS' THEN 'INFORMATICA'
        WHEN CD_CLASSE LIKE '26LIM' THEN 'LIMPEZA'
        WHEN CD_CLASSE LIKE '26LNB' THEN 'LINHA BRANCA'
        WHEN CD_CLASSE LIKE '26MOV' THEN 'MOVEIS'
        WHEN CD_CLASSE LIKE '26NVD' THEN 'NOTEBOOK'
        WHEN CD_CLASSE LIKE '26PAP' THEN 'PAPELARIA'
        WHEN CD_CLASSE LIKE '26PER' THEN 'PERFUMARIA'
        WHEN CD_CLASSE LIKE '26PET' THEN 'PETS & CIA'
        WHEN CD_CLASSE LIKE '26PNE' THEN 'PNEUS'
        WHEN CD_CLASSE LIKE '26PDE' THEN 'PONTA DE ESTOQUE'
        WHEN CD_CLASSE LIKE '26SAM' THEN 'LIMPEZA'
        WHEN CD_CLASSE LIKE '26TEC' THEN 'TECNICO'
        WHEN CD_CLASSE LIKE '26TV' THEN  'TV - IMAGEM'
        WHEN CD_CLASSE LIKE 'VND' THEN 'VENDIDOS'
        ELSE 'NAO CADASTRADO'
    END AS "DS_CLASSE_PRODUTO" FROM WIS50.T_CLASSE WHERE CD_CLASSE IN ('26AER','26ACE','26ALM','26BEB','26BDC','26COF','26COL','26DIV','26ECC','26FAR','26HIG','26EIS','26LIM','26LNB','26MOV','26NVD','26PAP','26PER','26PET','26PNE',  '26PDE','26SAM','26TEC','26TV',  'VND')) CLASSEE
    ON EE.CD_CLASSE = CLASSEE.CD_CLASSE
    
    
    
    LEFT JOIN                               (SELECT CD_TIPO_ENDERECO,DS_TIPO_ENDERECO,QT_CAPAC_PALETES,VL_ALTURA,VL_LARGURA,VL_PROFUNDIDADE,VL_PESO_MAXIMO FROM WIS50.T_TIPO_ENDERECO) TPE ON EE.CD_TIPO_ENDERECO = TPE.CD_TIPO_ENDERECO
    
    LEFT JOIN                               (SELECT CD_AREA_ARMAZ,DS_AREA_ARMAZ,DS_AREA_ERP  FROM WIS50.T_TIPO_AREA) TPA ON EE.CD_AREA_ARMAZ = TPA.CD_AREA_ARMAZ
    
    LEFT JOIN                               (SELECT CD_POSTO, CD_ENDERECO, CD_EMPRESA FROM WIS50.T_POSTO_ENDERECO WHERE CD_EMPRESA = 12650) TPE ON EE.CD_EMPRESA = TPE.CD_EMPRESA AND EE.CD_ENDERECO = TPE.CD_ENDERECO
    
    LEFT JOIN                               (SELECT CD_POSTO, DS_POSTO, CD_EMPRESA  FROM  WIS50.T_POSTO_TRABALHO WHERE CD_EMPRESA = 12650) TPT ON TPE.CD_EMPRESA = TPT.CD_EMPRESA AND TPE.CD_POSTO = TPT.CD_POSTO
    
                                WHERE
                                EE.CD_AREA_ARMAZ NOT IN ('98','6','8','35','4','5','87','32')
                                AND EE.CD_EMPRESA = 12650) EE ON DET.CD_EMPRESA = EE.CD_EMPRESA AND DET.CD_ENDERECO = EE.CD_ENDERECO
                                
                                
                                
LEFT JOIN                               (SELECT CD_PRODUTO, DS_PRODUTO, CD_FAMILIA, CD_LINHA, VL_ALTURA, VL_LARGURA, VL_PROFUNDIDADE, PS_BRUTO, CD_BARRAS_ORIGINAL FROM WIS50.T_CAB_PRODUTO) CAB ON DET.CD_PRODUTO = CAB.CD_PRODUTO
LEFT JOIN                               (SELECT CD_FAMILIA, DS_FAMILIA FROM WIS50.T_FAMILIA_PRODUTO) FA ON CAB.CD_FAMILIA = FA.CD_FAMILIA 
LEFT JOIN                               (SELECT CD_LINHA, DS_LINHA FROM WIS50.T_LINHA) LI ON CAB.CD_LINHA = LI.CD_LINHA 


WHERE

     TO_DATE(CASE WHEN TO_CHAR(DET.DT_SEPARACAO, 'HH24') BETWEEN  0 AND 5  THEN TO_CHAR(DET.DT_SEPARACAO-1,'YYYY-MM-DD')
            WHEN TO_CHAR(DET.DT_SEPARACAO, 'HH24') BETWEEN 22 AND 23 THEN TO_CHAR(DET.DT_SEPARACAO  ,'YYYY-MM-DD')
            WHEN TO_CHAR(DET.DT_SEPARACAO, 'HH24') BETWEEN  14 AND 21 THEN TO_CHAR(DET.DT_SEPARACAO  ,'YYYY-MM-DD')
            WHEN TO_CHAR(DET.DT_SEPARACAO, 'HH24') BETWEEN  6 AND 13 THEN TO_CHAR(DET.DT_SEPARACAO  ,'YYYY-MM-DD')
       END,'YYYY-MM-DD') >= TO_DATE(SYSDATE-7, 'YYYY-MM-DD')
       
       
    
    AND DET.NU_SEPARACAO = TO_NUMBER(SUBSTR(TR.VARIAVEL, 1, INSTR(TR.VARIAVEL, '#', 1) - 1))
    AND DET.CD_GRUPO_SEPARACAO = TO_NUMBER(SUBSTR(TR.VARIAVEL,
                        INSTR(TR.VARIAVEL, '#', 1, 1) + 1,
                        INSTR(TR.VARIAVEL, '#', 1, 2) -
                        INSTR(TR.VARIAVEL, '#', 1, 1) - 1))
    AND DET.CD_EMPRESA = TR.CD_EMPRESA
    AND EE.CD_ENDERECO NOT LIKE 'T99%'
  --  AND CAB.TP_PEDIDO = 'EPP'
   
 

GROUP BY
DET.CD_EMPRESA,
TO_CHAR(DET.DT_SEPARACAO, 'DD/MM/YYYY HH24'),
TO_CHAR(DET.DT_SEPARACAO, 'DD/MM/YYYY'),
TO_CHAR(DET.DT_SEPARACAO, 'HH24:MI:SS'),
TO_CHAR(DET.DT_SEPARACAO, 'HH24'),
EE.PREDIO,
EE.RUA,
TO_CHAR(EE.COLUNA,'000'),
EE.QUADRANTE,
EE.NIVEL,
EE.CD_ENDERECO,
DET.CD_PRODUTO,
CAB.DS_PRODUTO,
FA.DS_FAMILIA,
LI.DS_LINHA,
TR.CD_FUNCIONARIO,
FU.NM_FUNCIONARIO,
CASE EE.DS_POSTO
        WHEN 'MOVEIS  (28 - 33)' THEN 'MOVEIS'
        WHEN 'COFRE' THEN 'COFRE'
        WHEN 'DIVERSOS P (04 A 14)' THEN 'DIVERSOS'
        WHEN 'COLCHAO & ESTOFADO G18- G21)' THEN 'COLCHAO & ESTOFADO'
        WHEN 'PICKING COURIER (DIVERSOS)' THEN 'COURIER'
        WHEN 'LINHA BRANCA (21 - 27)' THEN 'LINHA BRANCA'
        WHEN 'TV + PNEU RUA 16 A 18' THEN 'TV E PNEU'
        WHEN 'MERCADO' THEN 'BENS DE CONSUMO'
        WHEN 'PICKING STAGER (ELETRO+ESTOFADO+COLCHAO)' THEN 'GRANPICK'
        WHEN 'GENERICO+DOCA+TEC' THEN 'GENERICO'
        ELSE EE.DS_POSTO
    END,
DET.DT_SEPARACAO,
DET.CD_CARGA,
CAB.NU_PEDIDO_ORIGEM,
TR.NU_TAREFA,
DET.NU_SEPARACAO,
DET.CD_GRUPO_SEPARACAO,
DET.CD_ENDERECO_DESTINO

ORDER BY
TR.CD_FUNCIONARIO ASC,
DET.DT_SEPARACAO ASC
    """
    data = await fetch_data_from_db(query, connection_string_wis)
    await update_google_sheet(data, '1A5KgKV-u7ZZB3RDWfhI3ULTh67Wm0H1JnNw9S-0iuqg', 'Base', 'A2:ac')
# Loop principal

async def update_agendas_pendentes():
    query ="""
    SELECT
  V1.CD_EMPRESA,
  TO_CHAR(V4.DT_AGENDAMENTO, 'DD/MM/YYYY') AS DATA_AGENDA,
  V1.CD_AGENDA,
  V4.ID_AGENDA_EXTERNA,
  CASE WHEN SUBSTR(V4.ID_AGENDA_EXTERNA, 1, 3) = 'INS' THEN 'LV'
       ELSE 'RECEBIMENTO'
  END AS TIPO_AGENDA,
  V2.CD_PRODUTO_MASTER,
  V3.DS_PRODUTO,
  V2.QT_PRODUTO,
  V2.QT_RECEBIDO,
  V2.QT_SOBRA
FROM
  WIS50.V_AGENDA_DIVERGENTE V1
LEFT JOIN
    WIS50.V_RECEBIMENTO_MASTER V2
 ON
  V1.CD_EMPRESA = V2.CD_EMPRESA
  AND V1.CD_AGENDA = V2.CD_AGENDA
LEFT JOIN
WIS50.T_CAB_PRODUTO V3
ON
  V2.CD_PRODUTO_MASTER = V3.CD_PRODUTO
LEFT JOIN
WIS50.T_AGENDA V4
ON
  V1.CD_EMPRESA = V4.CD_EMPRESA
  AND V1.CD_AGENDA = V4.CD_AGENDA
LEFT JOIN WIS50.T_CAB_NOTA_FISCAL V5
ON V1.CD_EMPRESA = V5.CD_EMPRESA
AND V1.CD_AGENDA = V5.CD_AGENDA
WHERE
  V1.CD_EMPRESA = 1590
  AND V2.CD_SITUACAO IN (10, 11)
    """
    data = await fetch_data_from_db(query, connection_string_wis)
    await update_google_sheet(data, '1ayDt8-Z0nPr-K325p3RHzdxq7bWw3pU0RLvm74EZRIo', 'AGENDAS EM ABERTO', 'A2:J')
# Loop principal

async def get_portaria():
    try:
        client = get_google_sheets_client('credentials.json')
        BASE_APP = client.open_by_key('1tsnR9l_giTiXJ9H4LY2-1WRSmc3Iu6Jl-oBhXC7NdPs')
        PORTARIA = BASE_APP.worksheet('PORTARIA')
        df = pd.read_csv('https://dash.magazineluiza.com.br/api/queries/6057/results.csv?api_key=HpdZuqVU2CSJj364l65B8rx9z0OvtFFhTAhFhQen')
        df = df.fillna('')
        PORTARIA.batch_clear(['A1:Z'])
        PORTARIA.update([df.columns.values.tolist()] + df.values.tolist(), 'A1')
        print('Portaria atualizada com sucesso!')
    except Exception as e:
        print('Erro ao atualizar portaria: ', e)

async def update_pendencia_5350():
    query = '''
SELECT
  TO_CHAR(ENT.DT_CONFERENCIA, 'DD/MM/YYYY HH24:MI') AS DATA_ENTRADA ,
  ENT.CD_AGENDA,
  ENT.NU_ETIQUETA_LOTE ETIQUETA,
  ROUND(TRUNC(SYSDATE) - TRUNC(ENT.DT_ADDROW)) DIAS,
  ENT.CD_PRODUTO,
  (
    SELECT
      CAB.DS_PRODUTO
    FROM
      WIS50.T_CAB_PRODUTO CAB
    WHERE
      ENT.CD_PRODUTO = CAB.CD_PRODUTO
  ) DS_PRODUTO,
  FUNC.NM_FUNCIONARIO,
  ENT.QT_CONFERIDO,
  'AGRUPADA' TP_ETIQUETA,
  ENT.CD_ENDERECO
FROM
  WIS50.T_DET_ETIQUETA_LOTE ENT
INNER JOIN WIS50.T_FUNCIONARIO FUNC ON ENT.CD_FUNC_CONFERENCIA = FUNC.CD_FUNCIONARIO
WHERE
  ENT.CD_EMPRESA = 15350
  AND ENT.CD_SITUACAO = 23
  AND ENT.CD_PRODUTO <> '11'
UNION ALL
SELECT
  TO_CHAR(ENT.DT_CONFERENCIA, 'DD/MM/YYYY HH24:MI') AS DATA_ENTRADA,
  ENT.CD_AGENDA,
  ENT.NU_ETIQUETA,
  ROUND(TRUNC(SYSDATE) - TRUNC(ENT.DT_ADDROW)) DIAS,
  ENT.CD_PRODUTO,
  (
    SELECT
      CAB.DS_PRODUTO
    FROM
      WIS50.T_CAB_PRODUTO CAB
    WHERE
      ENT.CD_PRODUTO = CAB.CD_PRODUTO
  ) DS_PRODUTO,
  FUNC.NM_FUNCIONARIO,
  ENT.QT_CONFERIDO,
  'NORMAL' TP_ETIQUETA,
  ENT.CD_ENDERECO
FROM
  WIS50.T_ETIQUETA_ENTRADA ENT
INNER JOIN WIS50.T_FUNCIONARIO FUNC ON ENT.CD_FUNC_CONFERENCIA = FUNC.CD_FUNCIONARIO
WHERE
  ENT.CD_EMPRESA = 15350
  AND ENT.CD_SITUACAO = 23
  AND ENT.CD_PRODUTO <> '11'
  AND ENT.CD_AREA_ARMAZ NOT IN (17, 9, 27)
ORDER BY
  DATA_ENTRADA
  
    '''
    data = await fetch_data_from_db(query, connection_string_wis)
    await update_google_sheet(data, '1M12Q3mTBCfElEw6ACUOGYBGyzlacIFA_ZmAdVWRmDco', '5350', 'A2:s')



async def main():
    date_max = datetime.now()
    while True:
        try:
            await asyncio.gather(
                update_grade(),
            )
            print("Dados atualizados com sucesso!")
        except Exception as e:
            print(f"Erro durante a atualização: {e}")

        await asyncio.sleep(300)

# Iniciar o loop principal
if __name__ == "__main__":
    asyncio.run(main())


