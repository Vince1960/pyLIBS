//---------------------------------------------------------------------------
#include <vcl.h>
#pragma hdrstop
#include <string.h>
#include <dstring.h>
#include "SDIMain.h"
#include "Unit1.h"
#include "Unit19.h"
//---------------------------------------------------------------------------
#pragma package(smart_init)
#pragma resource "*.dfm"
TForm19 *Form19;
//---------------------------------------------------------------------------
__fastcall TForm19::TForm19(TComponent* Owner)
    : TForm(Owner)
{
}
//---------------------------------------------------------------------------

void __fastcall TForm19::Button2Click(TObject *Sender)
{
Form19->Close();

}
//---------------------------------------------------------------------------
void __fastcall TForm19::Button1Click(TObject *Sender)
{
float minax,maxax,minay,maxay,delta;
delta=atof((OKBottomDlg->Edit8->Text).c_str());
 if (atof(ComboBox1->Text.c_str()) > 0)
{
 minax=atof(ComboBox1->Text.c_str())-delta;
  maxax=atof(ComboBox1->Text.c_str())+delta;
       SDIAppForm->Chart1->BottomAxis->SetMinMax(minax,maxax);
           SDIAppForm->Chart1->Refresh();
 minay=0;
 maxay=0;
  for (int pu=SDIAppForm->Series1->FirstValueIndex;pu <= SDIAppForm->Series1->LastValueIndex;pu++)
  {
  if (SDIAppForm->Series1->YValues->Value[pu] > maxay) maxay= SDIAppForm->Series1->YValues->Value[pu];
   }
  SDIAppForm->Chart1->LeftAxis->SetMinMax(minay,maxay);

  SDIAppForm->Chart1->LeftAxis->Automatic=false;
  SDIAppForm->Chart1->LeftAxis->SetMinMax(minay,maxay);
    SDIAppForm->Chart1->Refresh();
 }

  }
//---------------------------------------------------------------------------
