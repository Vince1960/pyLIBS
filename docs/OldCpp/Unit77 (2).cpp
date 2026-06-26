//---------------------------------------------------------------------------

#include <vcl.h>
#include <stdio.h>
#include <string.h>
#include <math.h>
#pragma hdrstop
#include "SDIMain.h"
#include "Unit2.h"
#include "Unit5.h"
#include "Unit6.h"
#include "Unit1.h"
#include "Unit77.h"
#define COLORE 12632150
//---------------------------------------------------------------------------
#pragma package(smart_init)
#pragma resource "*.dfm"
TForm7 *Form7;
//---------------------------------------------------------------------------
__fastcall TForm7::TForm7(TComponent* Owner)
        : TForm(Owner)
{
}
//---------------------------------------------------------------------------
void __fastcall TForm7::Button1Click(TObject *Sender)
{
    int rc;
    char sqls[300];
    int numlin;
   float fmin= atof(Form7->Edit2->Text.c_str());
    float fmax=  atof(Form7->Edit3->Text.c_str());


   // Counts the elements
 sprintf(sqls,"SELECT DISTINCT specie FROM datalibs WHERE wavelen > %s AND wavelen < %s",Form7->Edit2->Text, Form7->Edit3->Text);
  Form7->Query1->SQL->Clear();
 Form7->Query1->SQL->Add(sqls);
 Form7->Query1->Open();
 rc=Form7->Query1->RecordCount;
    Form7->Query1->First();
  //

    // Counts the lines in the interval
    numlin=Form6->Table1->RecordCount;
  //
   Form7->StringGrid2->ColCount=numlin+2;

  // Fill the Table with elements
   Form7->StringGrid2->RowCount=rc;
   for (int el=0; el < rc;el++){
  Form7->StringGrid2->Cells[0][el]=Form7->Query1->FieldValues["specie"];
  for (int ig=0;ig<numlin+1;ig++) Form7->StringGrid2->Cells[ig+1][el]=0;
  Form7->StringGrid1->Cells[0][el]="";
    Form7->StringGrid1->Cells[1][el]="";
    Form7->StringGrid1->Cells[2][el]="";
   Form7->Query1->Next();
   }
     Form7->Query1->Close();
      Form7->StringGrid1->Refresh();
     //


  // Repeat for all the lines
    Form6->Table1->First();
    for (int j=0;j<numlin;j++)  {
    float freq=Form6->Table1->FieldValues["wavelen"];

   // Find lines in the range
    if (freq >= fmin & freq <=fmax) {
    float range=atof(OKBottomDlg->Edit9->Text.c_str());
    sprintf(sqls,"SELECT * FROM datalibs WHERE [wavelen] BETWEEN %f AND %f ORDER BY abs([wavelen]-%f)",(freq-range),(freq+range),freq);
     Form5->Query1->SQL->Clear();
        Form5->Query1->SQL->Add(sqls);
          Form5->Query1->Open();
              rc=Form5->Query1->RecordCount;
              Form5->Query1->First();
    //

    // Calculates the score
          for (int k=0;k<rc;k++)  {
  float maxnt=Form5->Query1->FieldValues["inte"];
  int ioniz=Form5->Query1->FieldValues["ion"];
 AnsiString specie = Form5->Query1->FieldValues["specie"];
   sprintf(sqls,"SELECT * FROM datalibs WHERE [specie]='%s' AND [ion]= %i ORDER BY inte",specie,ioniz);

  Form7->Query1->SQL->Clear();
 Form7->Query1->SQL->Add(sqls);
 Form7->Query1->Open();
Form7->Query1->Last();
 float maxim=Form7->Query1->FieldValues["inte"];
   Form7->Query1->Close();

  float wave=Form5->Query1->FieldValues["wavelen"];

 float norma=maxnt/maxim;
    float rcc=30.000/(rc*1.0);
 float score= norma*log(rcc)*exp(-pow(wave-freq,2)/pow(2.*range,2));

 // Put score into the table

 for (int ii=0;ii<Form7->StringGrid2->RowCount;ii++) {

if  (Form7->StringGrid2->Cells[0][ii]==specie) {
     Form7->StringGrid2->Cells[j+1][ii]=score;
}
 }

 //


  Form5->Query1->Next();
             }
  //
         }
     Form6->Table1->Next();
    }

//

// Calculate total scores

for (int iii=0;iii<Form7->StringGrid2->RowCount;iii++) {

float sum=0;

    for (int jj=1;jj<numlin+1;jj++) {

    sum+=atof(Form7->StringGrid2->Cells[jj][iii].c_str());

    }

  Form7->StringGrid2->Cells[numlin+1][iii]=sum;

}

//

// Sort and display

Form7->StringGrid3->ColCount=2;
 Form7->StringGrid3->RowCount=Form7->StringGrid2->RowCount;

 for (int ik=0;ik<Form7->StringGrid2->RowCount;ik++) {
    Form7->StringGrid3->Cells[0][ik]=Form7->StringGrid2->Cells[0][ik];
   if ((Form7->StringGrid3->Cells[0][ik] != "H+") && (Form7->StringGrid3->Cells[0][ik] != "Al+")) {
    Form7->StringGrid3->Cells[1][ik]=Form7->StringGrid2->Cells[numlin+1][ik];
    }
    else
    {
    Form7->StringGrid3->Cells[1][ik]=0;
    }
   }

   int imax;
   for (int jj=0;jj<Form7->StringGrid2->RowCount;jj++) {
    float max=-100;
   for (int ij=0;ij<Form7->StringGrid2->RowCount;ij++) {
    if (atof(Form7->StringGrid3->Cells[1][ij].c_str()) >= max) {
    max=atof(Form7->StringGrid3->Cells[1][ij].c_str());
    imax=ij;
     }
   }
   Form7->StringGrid1->Cells[1][jj]= Form7->StringGrid3->Cells[0][imax];
   Form7->StringGrid1->Cells[2][jj]= Form7->StringGrid3->Cells[1][imax];
   Form7->StringGrid3->Cells[1][imax]=-1000;
   }

//

 }
//---------------------------------------------------------------------------

void __fastcall TForm7::FormShow(TObject *Sender)
{
     Form7->StringGrid1->ColWidths[0]=20;
Form7->StringGrid1->ColWidths[1]=30;
Form7->StringGrid1->ColWidths[2]=70;
Form7->Edit1->Text="10";
}
//---------------------------------------------------------------------------


void __fastcall TForm7::Edit1Change(TObject *Sender)
{
    Form7->StringGrid1->RowCount=atof(Form7->Edit1->Text.c_str());        
}
//---------------------------------------------------------------------------


void __fastcall TForm7::StringGrid1SelectCell(TObject *Sender, int ACol,
      int ARow, bool &CanSelect)
{
        if (StringGrid1->Cells[0][ARow]=="X")
                {
                StringGrid1->Cells[0][ARow]="";
                }
        else
                {
                StringGrid1->Cells[0][ARow]="X";

        }        
}
//---------------------------------------------------------------------------

void __fastcall TForm7::Button2Click(TObject *Sender)
{
  SDIAppForm->Series5->Clear();
for (int i=atoi(Form7->Edit1->Text.c_str())-1;i>=0;i--) {

AnsiString speci=Form7->StringGrid1->Cells[1][i];

//Calls Trace Routine

char lab[12];
 int rc,ind,ioniz;
 float maxnt,yval,maxscal;

char sqls[300];


sprintf(sqls,"SELECT * FROM datalibs WHERE [specie] = '%s' and [wavelen] > %f and [wavelen] < %f and [ion]=1 order by -[inte]",speci,SDIAppForm->Chart1->BottomAxis->Minimum,SDIAppForm->Chart1->BottomAxis->Maximum);
  Form5->Query1->SQL->Clear();
 Form5->Query1->SQL->Add(sqls);
 Form5->Query1->Open();
 if (Form5->Query1->RecordCount > 0 && Form7->StringGrid1->Cells[0][i] == "") {

 rc=Form5->Query1->RecordCount;
  if (rc > atof(Form7->Edit4->Text.c_str()))
  rc= atof(Form7->Edit4->Text.c_str());
 Form5->Query1->First();
 maxnt=Form5->Query1->FieldValues["inte"];
  maxscal=SDIAppForm->Chart1->LeftAxis->Maximum;
  for (ind=1;ind<rc+1;ind++)
  {
  ioniz=Form5->Query1->FieldValues["ion"];
  AnsiString specie = Form5->Query1->FieldValues["specie"];
  switch(ioniz)
  {
  case 1:
   sprintf(lab,"%s I",specie);
   break;
  case 2:
   sprintf(lab,"%s II",specie);
  break;
  }
  yval=float(Form5->Query1->FieldValues["inte"])*maxscal/maxnt;
  SDIAppForm->Series5->AddXY(Form5->Query1->FieldValues["wavelen"],yval,lab,clLime);
  Form5->Query1->Next();
  }
  Form5->Query1->First();

sprintf(sqls,"SELECT * FROM datalibs WHERE [specie] = '%s' AND [specie] <> 'H' AND [specie] <> 'H+' AND [wavelen] > %f AND [wavelen] < %f AND [ion]=2 ORDER BY -[inte]",speci,SDIAppForm->Chart1->BottomAxis->Minimum,SDIAppForm->Chart1->BottomAxis->Maximum);
  Form5->Query1->SQL->Clear();
 Form5->Query1->SQL->Add(sqls);
 Form5->Query1->Open();
 if (Form5->Query1->RecordCount > 0) {
 rc=Form5->Query1->RecordCount;
  if (rc > atof(Form7->Edit4->Text.c_str()))
  rc= atof(Form7->Edit4->Text.c_str());
 Form5->Query1->First();
 maxnt=Form5->Query1->FieldValues["inte"];
  maxscal=SDIAppForm->Chart1->LeftAxis->Maximum;
  for (ind=1;ind<rc+1;ind++)
  {
  ioniz=Form5->Query1->FieldValues["ion"];
  AnsiString specie = Form5->Query1->FieldValues["specie"];
  switch(ioniz)
  {
  case 1:
   sprintf(lab,"%s I",specie);
   break;
  case 2:
   sprintf(lab,"%s II",specie);
  break;
  }
  yval=float(Form5->Query1->FieldValues["inte"])*maxscal/maxnt;
  SDIAppForm->Series5->AddXY(Form5->Query1->FieldValues["wavelen"],yval,lab,clLime);
  Form5->Query1->Next();
  }
  Form5->Query1->First();
}
}
  SDIAppForm->Series5->Active=True;
  //

       }
  }

//---------------------------------------------------------------------------

void __fastcall TForm7::Button3Click(TObject *Sender)
{
char sqls[300];
 TLocateOptions Opts;
  Opts.Clear();
   Opts << loPartialKey << loCaseInsensitive;
 SDIAppForm->Chart1->BottomAxis->Automatic=false;
  float range=atof(OKBottomDlg->Edit9->Text.c_str());
   float oldmin= SDIAppForm->Chart1->BottomAxis->Minimum;
  float oldmax= SDIAppForm->Chart1->BottomAxis->Maximum;
 float freqw;
 int findx=SDIAppForm->Series5->FirstValueIndex;
  int lindx=SDIAppForm->Series5->LastValueIndex;
  for(int k=findx; k < lindx+1; k++)
{
 char sqls[300];
   AnsiString spe,io,ppp,sp;
    int lg;
    float soglia=atof(OKBottomDlg->Edit17->Text.c_str());
if (k < 0)
 break;

  freqw= SDIAppForm->Series5->XValues->Value[k];
  SDIAppForm->Chart1->BottomAxis->SetMinMax(freqw-range,freqw+range);
    SDIAppForm->Chart1->Refresh();
    int sm;
     float mind,dd;
     int s4f,s4l;

    if  (SDIAppForm->Series4->FirstValueIndex < 0)
     {
     goto pppp;
     }

     s4f=SDIAppForm->Series4->FirstValueIndex;
      s4l=SDIAppForm->Series4->LastValueIndex;

    if (s4f == s4l)
    {
    sm=s4f;
    }
    else if (s4l < s4f)
    {
    goto pppp;
    }
    else
    {
    sm=s4f;
    mind=1.e22;
    for (int z=s4f; z < s4l+1;z++)
    {
    dd=fabs(freqw-SDIAppForm->Series4->XValues->Value[z]);
    if (dd < mind)
    {
    mind=dd;
    sm=z;
    }
    }
    }


  Form6->Table1->RecNo=sm+1;


 if (Form6->Table1->FieldByName("Aki")->AsFloat >= soglia)
 {
 SDIAppForm->Series4->ValueColor[sm]=clYellow;
 }
 else
 {
  SDIAppForm->Series4->ValueColor[sm]=COLORE;
 }
 ppp=SDIAppForm->Series5->XLabel[k];

lg=StrLen(ppp.c_str());
 sp=ppp.SubString(lg-1,2);
 char label[10];
 if (sp != "II")
 {
  spe=ppp.SubString(1,lg-1);

  if (spe.SubString(lg-2,1)=="+")
        {
        spe=spe.SubString(1,lg-3);

        }
  io=AnsiString("1");
  sprintf(label,"%s I",spe);
  }
  else if ((sp=="II") & (lg==2))
 {
    spe="I";
     io=AnsiString("1");
     sprintf(label,"I I");
 }
 else
 {
 spe=ppp.SubString(1,lg-2);
 if (spe.SubString(lg-3,1)=="+")
        {
        spe=spe.SubString(1,lg-4);

        }
 io=AnsiString("2");
 sprintf(label,"%s II",spe);
 }

 SDIAppForm->Series4->XLabel[sm]=label;


  Form5->Edit1->Text=SDIAppForm->Series5->XValues->Value[k];
  Form5->Edit2->Text= spe;
  Form5->Edit3->Text= io;

  sprintf(sqls,"SELECT * FROM %s WHERE [ion]=%s AND [wavelen] BETWEEN %f-0.04 AND %f+0.04", Form5->Edit2->Text.c_str(),Form5->Edit3->Text.c_str(),atof(Form5->Edit1->Text.c_str()),atof(Form5->Edit1->Text.c_str()));

  Form5->Query2->SQL->Clear();
   Form5->Query2->SQL->Add(sqls);
     Form5->Query2->Open();
      Form5->Query2->First();
 SDIAppForm->Edit4->Text=FormatFloat("#0000.00",SDIAppForm->Series4->XValues->Value[sm]);
    if (Form5->Query2->RecordCount == 0)
    {
    }
else
{
 if (Form6->Table1->Locate("fitwavelen",SDIAppForm->Series4->XValues->Value[sm],Opts))
  {
  }
  else if (Form6->Table1->Locate("wavelen",SDIAppForm->Series4->XValues->Value[sm],Opts))
  {
  }
  else if (Form6->Table1->Locate("wavelen",SDIAppForm->Edit4->Text,Opts))
  {
  }
   else if (Form6->Table1->Locate("fitwavelen",SDIAppForm->Edit4->Text,Opts))
  {
  }
  else
  {
  // ShowMessage(SDIAppForm->Edit4->Text);
  }
Form6->Table1->Edit();
Form6->Table1->FieldValues["specie"]=Form5->Edit2->Text.c_str();
Form6->Table1->FieldValues["ion"]=Form5->Query2->FieldValues["ion"];
Form6->Table1->FieldValues["asswavelen"]=Form5->Query2->FieldByName("wavelen")->AsFloat;
Form6->Table1->FieldValues["Ek"]=Form5->Query2->FieldByName("Ek")->AsFloat;
Form6->Table1->FieldValues["acc"]=Form5->Query2->FieldValues["acc"];
if (Form6->Table1->FieldValues["Aki"] == -1.0)
{
if (Form5->Query2->FieldByName("Aki")->AsFloat !=0.0)
{
Form6->Table1->FieldValues["Aki"]=-Form5->Query2->FieldByName("Aki")->AsFloat;
}
else
{
Form6->Table1->FieldValues["Aki"]=-Form5->Query2->FieldByName("Aki")->AsFloat;
}
}
else
{
Form6->Table1->FieldValues["Aki"]=Form5->Query2->FieldByName("Aki")->AsFloat;
}
Form6->Table1->FieldValues["gk"]=Form5->Query2->FieldValues["gk"];
Form6->Table1->FieldValues["gi"]=Form5->Query2->FieldValues["gi"];
  Form6->Table1->Refresh();
// }
 //Form5->Query1->Next();
}
pppp:
}
 //  Form5->Query1->First();
  SDIAppForm->Chart1->BottomAxis->SetMinMax(oldmin,oldmax);
  SDIAppForm->Series5->Active=True;
  SDIAppForm->Series5->Clear();        
}
//---------------------------------------------------------------------------

void __fastcall TForm7::Button4Click(TObject *Sender)
{
Form7->Close();        
}
//---------------------------------------------------------------------------

