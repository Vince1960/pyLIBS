//---------------------------------------------------------------------------
#include <vcl.h>
#pragma hdrstop
#include <stdio.h>
#include "Unit9.h"
#include "Unit22.h"
//---------------------------------------------------------------------------
#pragma package(smart_init)
#pragma resource "*.dfm"
TForm22 *Form22;
//---------------------------------------------------------------------------
__fastcall TForm22::TForm22(TComponent* Owner)
    : TForm(Owner)
{
}
//---------------------------------------------------------------------------

void __fastcall TForm22::StringGrid1SelectCell(TObject *Sender, int Col,
      int Row, bool &CanSelect)
{
if (StringGrid1->Cells[0][Row]=="X")
{
StringGrid1->Cells[0][Row]="";
}
else
{
StringGrid1->Cells[0][Row]="X";
}  
}
//---------------------------------------------------------------------------

void __fastcall TForm22::Button2Click(TObject *Sender)
{
for (int i=1; i < Form22->StringGrid1->RowCount;i++)
{
Form22->StringGrid1->Cells[0][i]="";
}
}
//---------------------------------------------------------------------------
void __fastcall TForm22::Button3Click(TObject *Sender)
{
for (int i=1; i < Form22->StringGrid1->RowCount;i++)
{
Form22->StringGrid1->Cells[0][i]="X";
}
}
//---------------------------------------------------------------------------
void __fastcall TForm22::Button4Click(TObject *Sender)
{
Form22->Close();    
}
//---------------------------------------------------------------------------
void __fastcall TForm22::Button1Click(TObject *Sender)
{
int cnt=0;
 float tot=0.0;
  for (int i=1; i < Form22->StringGrid1->RowCount; i++)
{
if (Form22->StringGrid1->Cells[0][i] != "X" && atof(Form22->StringGrid1->Cells[2][i].c_str()) !=0.0)
{
cnt++;
 tot+=atof(Form22->StringGrid1->Cells[2][i].c_str());
}
}
if (cnt !=0)
{
char dm[20];
sprintf(dm,"%1.3f",tot/cnt);
 Form9->Edit11->Text=dm;
 }
else
{
 Form9->Edit11->Text="";
}
Form9->Edit8->Text="";
Form9->Edit8->Text=Form9->Edit12->Text;
}
//---------------------------------------------------------------------------

