//---------------------------------------------------------------------------

#include <vcl.h>
#pragma hdrstop
#include <algorithm>
#include "SDIMain.h"
#include "Unit13.h"
#include "Unit25.h"
//---------------------------------------------------------------------------
#pragma package(smart_init)
#pragma resource "*.dfm"
TForm13 *Form13;
//---------------------------------------------------------------------------
__fastcall TForm13::TForm13(TComponent* Owner)
        : TForm(Owner)
{
}
//---------------------------------------------------------------------------

void __fastcall TForm13::StringGrid1Click(TObject *Sender)
{
int rw=Form13->StringGrid1->Row;
     AnsiString nm;
	  AnsiString cp="";

         int ru;

 // if (rw==0) return;
  Form13->Edit1->Text=Form13->StringGrid1->Cells[Form13->StringGrid1->Col][Form13->StringGrid1->Row];
// Form25->Show();
}
//---------------------------------------------------------------------------

void __fastcall TForm13::Button1Click(TObject *Sender)
{
void exc();
exc();
}
//---------------------------------------------------------------------------

void __fastcall TForm13::Button2Click(TObject *Sender)
{
if (Form13->Edit1->Text == "")
 {
 ShowMessage ("No spectrum selected");
 return;
    }

 int rw=Form13->StringGrid1->Row;
     AnsiString nm;
      AnsiString cp="";
         int ru;
if (rw==0)
 {
 ShowMessage ("Main spectrum should be always visible");
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

void __fastcall TForm13::Button3Click(TObject *Sender)
{int colo[34]={clRed,clGreen,clBlue,clPurple,clGray,clMaroon,clNavy,clOlive,clLtGray,clFuchsia,clWhite,clTeal,clSilver,clLime,clAqua,clBlack+200,clRed+200,clGray+200,clAqua+200,clBlue+200,clGreen+200,clBlack+200,clMaroon+200,clNavy+200,clDkGray+200,clOlive+200,clPurple+200,clLtGray+200,clFuchsia+200,clWhite+200,clTeal+200,clSilver+200,clLime+200};

      if (Form13->Edit1->Text == "") return;
            AnsiString nm;
      AnsiString cp="";
      int ru=0;
      int rw=Form13->StringGrid1->Row;
      if (rw==0)
     { ru=0;
      goto iii;
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
 iii:
  int sc=SDIAppForm->Chart1->SeriesCount();
      TLineSeries *MySeries = new TLineSeries(SDIAppForm);
         MySeries->ParentChart=SDIAppForm->Chart1;
    MySeries->LinePen->Style=psSolid;
      MySeries->SeriesColor=colo[sc-6];

          MySeries->Active=true;
           MySeries->XValues->Order = loAscending;
           MySeries->Clear();
           AnsiString sd = "";
                sd.cat_sprintf("s%i", sc-5);

            MySeries->Name=sd;

for (int q=0; q < SDIAppForm->Chart1->Series[ru]->Count();q++)
{
   MySeries->AddXY(SDIAppForm->Chart1->Series[ru]->XValues->Value[q],SDIAppForm->Chart1->Series[ru]->YValues->Value[q]+atof(AnsiString(Form13->Edit2->Text).c_str()),' ',colo[sc-6]);
 }

 MySeries->Active=true;

 Form13->StringGrid1->Cells[1][sc-5]="Shifted";
SDIAppForm->Chart1->Refresh();
return;
}
//---------------------------------------------------------------------------


void __fastcall TForm13::StringGrid1MouseDown(TObject *Sender,
      TMouseButton Button, TShiftState Shift, int X, int Y)
{
int rw=Form13->StringGrid1->Row;
if (Shift.Contains(ssCtrl)&&Form13->StringGrid1->Cells[1][rw]!="")
{
if (Form13->StringGrid1->Cells[0][rw] =="") Form13->StringGrid1->Cells[0][rw] ="X";
else  Form13->StringGrid1->Cells[0][rw] ="";
}
}
//---------------------------------------------------------------------------

void __fastcall TForm13::Button4Click(TObject *Sender)
{
int colo[34]={clRed,clGreen,clBlue,clPurple,clGray,clMaroon,clNavy,clOlive,clLtGray,clFuchsia,clWhite,clTeal,clSilver,clLime,clAqua,clBlack+200,clRed+200,clGray+200,clAqua+200,clBlue+200,clGreen+200,clBlack+200,clMaroon+200,clNavy+200,clDkGray+200,clOlive+200,clPurple+200,clLtGray+200,clFuchsia+200,clWhite+200,clTeal+200,clSilver+200,clLime+200};
int sc=SDIAppForm->Chart1->SeriesCount();
       int count=0;
       int jfin;
  for (int j=0;j<=Form13->StringGrid1->RowCount;j++)
  {
  if   (Form13->StringGrid1->Cells[0][j] =="X") count++;
  if   (Form13->StringGrid1->Cells[1][j] =="")
  {
  jfin=j;
  goto ou;
  }
  }
ou:
if (count < 2)
     {
 ShowMessage ("At least two specta must be selected");
 return;
    }
      TLineSeries *MySeries = new TLineSeries(SDIAppForm);
         MySeries->ParentChart=SDIAppForm->Chart1;
    MySeries->LinePen->Style=psSolid;
      MySeries->SeriesColor=colo[sc-6];
      
          MySeries->Active=true;
           MySeries->XValues->Order = loAscending;
           MySeries->Clear();
           AnsiString sd = "";
                sd.cat_sprintf("s%i", sc-5);

            MySeries->Name=sd;

            if   (Form13->StringGrid1->Cells[0][0] =="X") for (int jj=0;jj<SDIAppForm->Series1->Count();jj++) MySeries->AddXY(SDIAppForm->Series1->XValues->Value[jj],SDIAppForm->Series1->YValues->Value[jj],' ',colo[sc-6]);
            else
            {
            for (int jj=0;jj<SDIAppForm->Series1->Count();jj++) MySeries->AddXY(SDIAppForm->Series1->XValues->Value[jj],0.0,' ',colo[sc-6]);
            }


 if (count >1)
 {
 Form13->StringGrid1->Col=1;
 Form13->StringGrid1->Row=jfin;
 Form13->StringGrid1->Cells[1][jfin]="Average";
  }

 for (int j=1;j<Form13->StringGrid1->RowCount;j++)
 {
 if (Form13->StringGrid1->Cells[0][j] =="X")
 {
 AnsiString cp="";
 AnsiString nm;
     int ru;
     cp.cat_sprintf("s%i",j);

   for (int u=0; u < SDIAppForm->Chart1->SeriesCount();u++)
   {
   nm=SDIAppForm->Chart1->Series[u]->Name;
    if (nm == cp)
    {
    ru=u;
    break;
    }
 }

 for (int jj=0;jj<SDIAppForm->Series1->Count();jj++) MySeries->YValues->Value[jj]+=SDIAppForm->Chart1->Series[ru]->YValues->Value[jj];
 }
 }
  for (int jj=0;jj<SDIAppForm->Series1->Count();jj++) MySeries->YValues->Value[jj]/=count;

  Form13->StringGrid1->Refresh();
   MySeries->Active=true;
}
//---------------------------------------------------------------------------

void __fastcall TForm13::Button6Click(TObject *Sender)
{
int colo[34]={clRed,clGreen,clBlue,clPurple,clGray,clMaroon,clNavy,clOlive,clLtGray,clFuchsia,clWhite,clTeal,clSilver,clLime,clAqua,clBlack+200,clRed+200,clGray+200,clAqua+200,clBlue+200,clGreen+200,clBlack+200,clMaroon+200,clNavy+200,clDkGray+200,clOlive+200,clPurple+200,clLtGray+200,clFuchsia+200,clWhite+200,clTeal+200,clSilver+200,clLime+200};
int sc=SDIAppForm->Chart1->SeriesCount();
            int count=0;
            int jfin;
  for (int j=0;j<=Form13->StringGrid1->RowCount;j++)
  {
  if   (Form13->StringGrid1->Cells[0][j] =="X") count++;
  if   (Form13->StringGrid1->Cells[1][j] =="")
  {
  jfin=j;
  goto ou;
  }
  }
ou:
if (count < 2)
     {
 ShowMessage ("At least two specta must be selected");
 return;
    }
      TLineSeries *MySeries = new TLineSeries(SDIAppForm);
         MySeries->ParentChart=SDIAppForm->Chart1;
    MySeries->LinePen->Style=psSolid;
      MySeries->SeriesColor=colo[sc-6];

          MySeries->Active=true;
           MySeries->XValues->Order = loAscending;
           MySeries->Clear();
           AnsiString sd = "";
                sd.cat_sprintf("s%i", sc-5);

            MySeries->Name=sd;

            if   (Form13->StringGrid1->Cells[0][0] =="X") for (int jj=0;jj<SDIAppForm->Series1->Count();jj++) MySeries->AddXY(SDIAppForm->Series1->XValues->Value[jj],SDIAppForm->Series1->YValues->Value[jj],' ',colo[sc-6]);
            else
            {
            for (int jj=0;jj<SDIAppForm->Series1->Count();jj++) MySeries->AddXY(SDIAppForm->Series1->XValues->Value[jj],-1.e17,' ',colo[sc-6]);
            }

 if (count >1)
 {
 Form13->StringGrid1->Col=1;
 Form13->StringGrid1->Row=jfin;
 Form13->StringGrid1->Cells[1][jfin]="Max";
  }

 for (int j=1;j<Form13->StringGrid1->RowCount;j++)
 {
 if (Form13->StringGrid1->Cells[0][j] =="X")
 {
 AnsiString cp="";
 AnsiString nm;
     int ru;
     cp.cat_sprintf("s%i",j);

   for (int u=0; u < SDIAppForm->Chart1->SeriesCount();u++)
   {
   nm=SDIAppForm->Chart1->Series[u]->Name;
    if (nm == cp)
    {
    ru=u;
    break;
    }
 }

 for (int jj=0;jj<SDIAppForm->Series1->Count();jj++)
 if (MySeries->YValues->Value[jj]<SDIAppForm->Chart1->Series[ru]->YValues->Value[jj]) MySeries->YValues->Value[jj]=SDIAppForm->Chart1->Series[ru]->YValues->Value[jj];
 }
 }

  Form13->StringGrid1->Refresh();
   MySeries->Active=true;
}
//---------------------------------------------------------------------------

void __fastcall TForm13::Button5Click(TObject *Sender)
{
int colo[34]={clRed,clGreen,clBlue,clPurple,clGray,clMaroon,clNavy,clOlive,clLtGray,clFuchsia,clWhite,clTeal,clSilver,clLime,clAqua,clBlack+200,clRed+200,clGray+200,clAqua+200,clBlue+200,clGreen+200,clBlack+200,clMaroon+200,clNavy+200,clDkGray+200,clOlive+200,clPurple+200,clLtGray+200,clFuchsia+200,clWhite+200,clTeal+200,clSilver+200,clLime+200};
int sc=SDIAppForm->Chart1->SeriesCount();
                int count=0;
                int jfin;
  for (int j=0;j<=Form13->StringGrid1->RowCount;j++)
  {
  if   (Form13->StringGrid1->Cells[0][j] =="X") count++;
  if   (Form13->StringGrid1->Cells[1][j] =="")
  {
  jfin=j;
  goto ou;
  }
  }
ou:
if (count < 2)
     {
 ShowMessage ("At least two specta must be selected");
 return;
    }

      TLineSeries *MySeries = new TLineSeries(SDIAppForm);
         MySeries->ParentChart=SDIAppForm->Chart1;
    MySeries->LinePen->Style=psSolid;
      MySeries->SeriesColor=colo[sc-6];

          MySeries->Active=true;
           MySeries->XValues->Order = loAscending;
           MySeries->Clear();
           AnsiString sd = "";
                sd.cat_sprintf("s%i", sc-5);

            MySeries->Name=sd;

            if   (Form13->StringGrid1->Cells[0][0] =="X") for (int jj=0;jj<SDIAppForm->Series1->Count();jj++) MySeries->AddXY(SDIAppForm->Series1->XValues->Value[jj],SDIAppForm->Series1->YValues->Value[jj],' ',colo[sc-6]);
            else
            {
            for (int jj=0;jj<SDIAppForm->Series1->Count();jj++) MySeries->AddXY(SDIAppForm->Series1->XValues->Value[jj],1.e17,' ',colo[sc-6]);
            }


 if (count >1)
 {
 Form13->StringGrid1->Col=1;
 Form13->StringGrid1->Row=jfin;
 Form13->StringGrid1->Cells[1][jfin]="Min";
  }

 for (int j=1;j<Form13->StringGrid1->RowCount;j++)
 {
 if (Form13->StringGrid1->Cells[0][j] =="X")
 {
 AnsiString cp="";
 AnsiString nm;
     int ru;
     cp.cat_sprintf("s%i",j);

   for (int u=0; u < SDIAppForm->Chart1->SeriesCount();u++)
   {
   nm=SDIAppForm->Chart1->Series[u]->Name;
    if (nm == cp)
    {
    ru=u;
    break;
    }
 }

 for (int jj=0;jj<SDIAppForm->Series1->Count();jj++)
 if (MySeries->YValues->Value[jj]>SDIAppForm->Chart1->Series[ru]->YValues->Value[jj]) MySeries->YValues->Value[jj]=SDIAppForm->Chart1->Series[ru]->YValues->Value[jj];
 }
 }

  Form13->StringGrid1->Refresh();
   MySeries->Active=true;
}
//---------------------------------------------------------------------------

void __fastcall TForm13::Button7Click(TObject *Sender)
{
int colore;
if (Form13->Edit1->Text == "")
 {
 ShowMessage ("No spectrum selected");
 return;
    }


 int rw=Form13->StringGrid1->Row;
 if (rw==0)
 {
 ShowMessage ("Cannot change color of the main spectrum");
 return;
    }

    if (SDIAppForm->ColorDialog1->Execute())
    colore = SDIAppForm->ColorDialog1->Color;
     AnsiString nm;
      AnsiString cp="";
         int ru;
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
 for (int jj=0;jj<SDIAppForm->Chart1->Series[ru]->Count();jj++) SDIAppForm->Chart1->Series[ru]->ValueColor[jj]=colore;
}
//---------------------------------------------------------------------------


void __fastcall TForm13::Button8Click(TObject *Sender)
{
int colo[34]={clRed,clGreen,clBlue,clPurple,clGray,clMaroon,clNavy,clOlive,clLtGray,clFuchsia,clWhite,clTeal,clSilver,clLime,clAqua,clBlack+200,clRed+200,clGray+200,clAqua+200,clBlue+200,clGreen+200,clBlack+200,clMaroon+200,clNavy+200,clDkGray+200,clOlive+200,clPurple+200,clLtGray+200,clFuchsia+200,clWhite+200,clTeal+200,clSilver+200,clLime+200};

      if (Form13->Edit1->Text == "") return;
            AnsiString nm;
      AnsiString cp="";
      int ru=0;
      int rw=Form13->StringGrid1->Row;
      if (rw==0)
     { ru=0;
      goto iii;
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
 iii:
  int sc=SDIAppForm->Chart1->SeriesCount();
      TLineSeries *MySeries = new TLineSeries(SDIAppForm);
         MySeries->ParentChart=SDIAppForm->Chart1;
    MySeries->LinePen->Style=psSolid;
      MySeries->SeriesColor=colo[sc-6];

          MySeries->Active=true;
           MySeries->XValues->Order = loAscending;
           MySeries->Clear();
           AnsiString sd = "";
                sd.cat_sprintf("s%i", sc-5);

            MySeries->Name=sd;

for (int q=0; q < SDIAppForm->Chart1->Series[ru]->Count();q++)
{
   MySeries->AddXY(SDIAppForm->Chart1->Series[ru]->XValues->Value[q],SDIAppForm->Chart1->Series[ru]->YValues->Value[q]*atof(AnsiString(Form13->Edit3->Text).c_str()),' ',colo[sc-6]);
 }

 MySeries->Active=true;

 Form13->StringGrid1->Cells[1][sc-5]="Scaled";
SDIAppForm->Chart1->Refresh();
return;
}
//---------------------------------------------------------------------------

void __fastcall TForm13::Button9Click(TObject *Sender)
{
void swap();
swap();
}
//---------------------------------------------------------------------------

void __fastcall TForm13::Button10Click(TObject *Sender)
{
void deleteseries();
deleteseries();        
}
//---------------------------------------------------------------------------

