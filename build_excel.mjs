import fs from 'node:fs/promises';
import path from 'node:path';
import { Workbook, SpreadsheetFile } from '@oai/artifact-tool';

const input = process.argv[2];
const data = JSON.parse(await fs.readFile(input,'utf8'));
const outputDir = path.dirname(input);
const verify = process.argv.includes('--verify');
const wb = Workbook.create();
const sheets = Object.fromEntries(['Rotas','Comprar','Vender','Dados'].map(n=>[n,wb.worksheets.add(n)]));
const stamp = new Date(data.generated*1000).toLocaleString('pt-BR',{timeZone:'America/Fortaleza'});
const header=6, start=7;
const col = n => {let s=''; for(n++;n;n=Math.floor((n-1)/26))s=String.fromCharCode(65+(n-1)%26)+s;return s;};
function base(sheet,title,subtitle,headers,count){
  const end = Math.max(start,header+count), last = col(headers.length-1);
  sheet.showGridLines=false;
  sheet.getRange(`A1:${last}${end}`).format.font={name:'Arial',size:10,color:'#DFE8F4'};
  sheet.getRange(`A1:${last}${end}`).format.fill='#111C2B';
  sheet.getRange(`A1:${last}${end}`).format.rowHeight=25;
  sheet.getRange(`A1:${last}${end}`).format.verticalAlignment='center';
  sheet.getRange('A1').values=[[title]];
  sheet.getRange('A1').format.font={name:'Arial',size:17,bold:true,color:'#FFFFFF'};
  sheet.getRange('A2').values=[[subtitle]];
  sheet.getRange(`A${header}:${last}${header}`).values=[headers];
  sheet.getRange(`A${header}:${last}${header}`).format={fill:'#81B7A6',font:{name:'Arial',size:10,bold:true,color:'#10251F'},wrapText:true,rowHeight:42};
  sheet.getRange(`A${start}:${last}${end}`).format.rowHeight=33;
  sheet.getRange(`A${start}:A${end}`).format.wrapText=true;
  sheet.getRange(`A1:A${end}`).format.columnWidth=40;
  sheet.getRange(`B1:${last}${end}`).format.columnWidth=18;
  sheet.freezePanes.freezeRows(header);
  if(count) sheet.tables.add(`A${header}:${last}${end}`,true,`Tabela${sheet.name}`);
  return end;
}

const routes=sheets.Rotas;
let end=base(routes,'Onde comprar e vender',`Américas • ${stamp} (Fortaleza) • Valores em prata por unidade`,
 ['Equipamento / tier','Qualidade','Comprar em','Compra / un.','Vender em','Venda / un.','Qtd. compra','Qtd. venda','Qtd. limite','Margem bruta / un.','Após custos / un.','Retorno sobre compra','Resultado do lote','Idade compra (min)','Idade venda (min)','Código'],data.routes.length);
routes.getRange('A3:F3').values=[['Taxa de venda',data.tax,'Transporte / un.',data.transport,'Idade máxima (min)',data.minutes]];
routes.getRange('B3').setNumberFormat('0.0%');
routes.getRange('B3').format.fill='#725D21';routes.getRange('D3').format.fill='#725D21';
routes.getRange('A4').values=[['Taxa e transporte começam em zero: configure no monitor. O arquivo é regenerado; salve uma cópia para editar.']];
routes.getRange('A5').values=[['Melhor rota por margem/unidade entre mercados diferentes, dentro dos filtros. Quantidades e preços são observados.']];
routes.getRange('C7:C'+end).format.wrapText=true;routes.getRange('E7:E'+end).format.wrapText=true;
routes.getRange('P1:P'+end).format.columnWidth=36;
if(data.routes.length){
 const values=data.routes.map(r=>[`${r.name} ${r.code.split('_')[0]}.${r.enchantment}`,r.quality_name,r.origin,r.buy.price,r.destination,r.sell.price,r.buy.amount,r.sell.amount,null,null,null,null,null,(data.generated-r.buy.seen)/60,(data.generated-r.sell.seen)/60,r.code]);
 routes.getRange(`A7:P${end}`).values=values;
 routes.getRange(`I7:M${end}`).formulas=data.routes.map((r,i)=>{const n=i+7;return [`=MIN(G${n},H${n})`,`=F${n}-D${n}`,`=F${n}*(1-$B$3)-D${n}-$D$3`,`=K${n}/D${n}`,`=K${n}*I${n}`];});
 routes.getRange(`D7:K${end}`).setNumberFormat('#,##0.00');
 routes.getRange(`G7:I${end}`).setNumberFormat('#,##0');
 routes.getRange(`L7:L${end}`).setNumberFormat('0.0%');
 routes.getRange(`M7:M${end}`).setNumberFormat('#,##0.00');
 routes.getRange(`N7:O${end}`).setNumberFormat('0.0');
 routes.getRange(`K7:K${end}`).conditionalFormats.add('cellIs',{operator:'greaterThan',formula:0,format:{fill:'#24583F',font:{color:'#E5FFF0'}}});
 routes.getRange(`K7:K${end}`).conditionalFormats.add('cellIs',{operator:'lessThanOrEqual',formula:0,format:{fill:'#753B3B',font:{color:'#FFFFFF'}}});
}else routes.getRange('A7').values=[['Aguardando preços dos dois lados em mercados diferentes.']];

for(const [sheetName,side,title] of [['Comprar','offer','Quanto custa comprar'],['Vender','request','Quanto pagam para você vender']]){
 const sheet=sheets[sheetName];
 const headings=['Equipamento / tier','Qualidade',...data.cities.map(c=>c[1]),side==='offer'?'Menor preço':'Maior preço','Cidade','Código'];
 const end=base(sheet,title,`Américas • ${stamp} • Prata por unidade • Apenas observações de até ${data.minutes} min`,headings,data.variants.length);
 sheet.getRange('A3').values=[[side==='offer'?'Menor oferta de venda por cidade: preço para comprar imediatamente.':'Maior ordem de compra por cidade: preço para vender imediatamente.']];
 sheet.getRange('A4').values=[['Célula vazia = sem observação recente. Idades e quantidades de cada preço estão na aba Dados.']];
 const filters=data.filters??{};
 sheet.getRange('A5').values=[[`Filtros: item ${filters.query||'todos'}; cidade ${filters.market||'todas'}; tier ${filters.tier||'todos'}; encantamento ${filters.enchant||'todos'}; qualidade ${filters.quality||'todas'}. ${data.equipment_only?'Somente equipamentos.':'Todos os tipos.'}`]];
 if(data.variants.length){
   sheet.getRange(`A7:M${end}`).values=data.variants.map(v=>[`${v.name} ${v.code.split('_')[0]}.${v.enchantment}`,v.quality_name,
      ...data.cities.map(([id])=>v.markets[id]?.[side]?.price??null),null,null,v.code]);
   sheet.getRange(`K7:L${end}`).formulas=data.variants.map((v,i)=>{const n=i+7;return [
     `=IF(COUNT(C${n}:J${n})=0,"",${side==='offer'?'MIN':'MAX'}(C${n}:J${n}))`,
     `=IF(COUNT(C${n}:J${n})=0,"",INDEX($C$6:$J$6,1,MATCH(K${n},C${n}:J${n},0)))`];});
   sheet.getRange(`C7:K${end}`).setNumberFormat('#,##0');
   sheet.getRange(`K7:L${end}`).format.fill='#1C3558';
   for(let n=7;n<=end;n++)sheet.getRange(`C${n}:J${n}`).conditionalFormats.addCustom(
       `AND(ISNUMBER(C${n}),C${n}=$K${n})`,{fill:'#295B43',font:{color:'#FFFFFF'}});
 }else sheet.getRange('A7').values=[['Aguardando coleta de equipamentos.']];
 sheet.getRange(`L1:L${end}`).format.columnWidth=22;
 sheet.getRange(`M1:M${end}`).format.columnWidth=38;
}

const raw=sheets.Dados;
end=base(raw,'Preços usados na análise',`Américas • ${stamp} • Idade calculada no momento da exportação`,
 ['Equipamento','Código','Qualidade','Encantamento','Cidade','ID mercado','Tipo de ordem','Prata / un.','Qtd. neste preço','Recebido (Fortaleza)','Idade (min)','Fonte'],data.observations.length);
raw.getRange('A3').values=[['Fonte de preços: https://www.albion-online-data.com/developer — marketorders.deduped, Américas']];
raw.getRange('A4').values=[['Nomes: https://github.com/ao-data/ao-bin-dumps/tree/master/formatted']];
raw.getRange('A5').values=[['Mercados: https://github.com/ao-data/albiondata-server-rails/blob/main/lib/location.rb']];
raw.getRange('B1:B'+end).format.columnWidth=36;raw.getRange('J1:J'+end).format.columnWidth=23;
raw.getRange('L1:L'+end).format.columnWidth=55;
if(data.observations.length){
 raw.getRange(`A7:L${end}`).values=data.observations.map(o=>[o.name,o.code,o.quality,o.enchantment,o.city,o.city_id,
   o.side==='offer'?'Oferta de venda':'Ordem de compra',o.price,o.amount,
   new Date((o.seen-10800)*1000),(data.generated-o.seen)/60,'https://www.albion-online-data.com/developer']);
 raw.getRange(`H7:I${end}`).setNumberFormat('#,##0');raw.getRange(`J7:J${end}`).setNumberFormat('dd/mm/yyyy hh:mm:ss');raw.getRange(`K7:K${end}`).setNumberFormat('0.0');
 raw.getRange(`K7:K${end}`).conditionalFormats.add('cellIs',{operator:'greaterThan',formula:5,format:{fill:'#735325',font:{color:'#FFFFFF'}}});
}

if(verify){
 console.log((await wb.inspect({kind:'table',range:'Rotas!A6:P10',include:'values,formulas',tableMaxRows:5,tableMaxCols:16,maxChars:3500})).ndjson);
 const errors=await wb.inspect({kind:'match',searchTerm:'#REF!|#DIV/0!|#VALUE!|#NAME\\?|#N/A|#NUM!|#NULL!|#SPILL!|#CALC!',options:{useRegex:true,maxResults:20},summary:'Formula errors'});
 console.log(errors.ndjson);
 for(const sheetName of ['Rotas','Comprar','Vender','Dados']){
   const image=await wb.render({sheetName,range:sheetName==='Rotas'?'A1:P12':sheetName==='Dados'?'A1:L12':'A1:M12',scale:1,format:'png'});
   await fs.writeFile(path.join(outputDir,`${sheetName}.png`),new Uint8Array(await image.arrayBuffer()));
 }
}
const file=await SpreadsheetFile.exportXlsx(wb);
const pending=path.join(outputDir,'Mercado_Americas.pending.xlsx');
await file.save(pending);
try{await fs.rename(pending,path.join(outputDir,'Mercado_Americas.xlsx'));}
catch(error){if(['EPERM','EACCES','EBUSY'].includes(error.code)){console.error('Arquivo Excel bloqueado.');process.exit(3);}throw error;}
console.log(JSON.stringify({variants:data.variants.length,routes:data.routes.length,observations:data.observations.length}));
