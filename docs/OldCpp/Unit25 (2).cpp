//---------------------------------------------------------------------------

#include <vcl.h>
#pragma hdrstop
#include "SDIMain.h"
#include "Unit25.h"
#include "Unit13.h"
//---------------------------------------------------------------------------
#pragma package(smart_init)
#pragma resource "*.dfm"
TForm25 *Form25;
//---------------------------------------------------------------------------
__fastcall TForm25::TForm25(TComponent* Owner)
        : TForm(Owner)
{
}
//---------------------------------------------------------------------------





void __fastcall TForm25::Button2Click(TObject *Sender)
{
 int rw=Form13->StringGrid1->Row;
     AnsiString nm;
      AnsiString cp="";
         int ru;
if (rw==0)
{
if (SDIAppForm->Series1->Active==False)
{
SDIAppForm->Series1->Active=True;
}
else SDIAppForm->Series1->Active=False;
return;
}
       cp.cat_sprintf("s%i",rw);

   for (int u=0; u < SDIAppForm->Chart1->SeriesCount();u++)
   {
   nm=SDIAppForm->Chart1->Series[u]->Name;
    if (nm == cp)
    {
    ru=u;
    break;
    }
 }
if (SDIAppForm->Chart1->Series[ru]->Active==False)
{
SDIAppForm->Chart1->Series[ru]->Active=True;
}
else SDIAppForm->Chart1->Series[ru]->Active=False;
}
//---------------------------------------------------------------------------

